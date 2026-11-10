import base64
import hashlib
from base64 import b64decode
from io import BytesIO

from markupsafe import Markup
from PyPDF2 import PdfFileReader

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_escape


class PontonEventContract(models.Model):
    _name = 'ponton.event.contract'
    _description = 'Contrato de evento'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    event_id = fields.Many2one('event.event', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='event_id.company_id', store=True, readonly=True)
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('generated', 'Generado'),
            ('sent', 'Enviado'),
            ('signed', 'Firmado'),
            ('cancelled', 'Cancelado'),
            ('expired', 'Vencido'),
            ('obsolete', 'Obsoleto'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )
    version = fields.Integer(default=1, readonly=True)
    body_html = fields.Html('Texto congelado', readonly=True)
    body_hash = fields.Char('Hash texto', readonly=True, copy=False)
    source_hash = fields.Char('Hash PDF base legado', readonly=True, copy=False)
    pdf_hash = fields.Char('Hash PDF base', readonly=True, copy=False)
    pdf_attachment_id = fields.Many2one('ir.attachment', string='PDF base', readonly=True, copy=False)
    signed_attachment_id = fields.Many2one('ir.attachment', string='PDF firmado', readonly=True, copy=False)
    sign_oca_request_id = fields.Many2one('sign.oca.request', string='Solicitud OCA Sign', readonly=True, copy=False)
    signed_at = fields.Datetime('Firmado el', readonly=True, copy=False)
    signed_hash = fields.Char('Hash firmado', readonly=True, copy=False)
    expires_at = fields.Datetime('Vence para firma', readonly=True, copy=False)

    def action_generate_pdf(self):
        for contract in self:
            pdf, _report_type = self.env['ir.actions.report']._render_qweb_pdf(
                'ponton_event_contracts.action_report_ponton_event_contract',
                [contract.id],
            )
            attachment = self.env['ir.attachment'].create({
                'name': f'{contract.name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf),
                'res_model': contract._name,
                'res_id': contract.id,
                'mimetype': 'application/pdf',
            })
            pdf_hash = hashlib.sha256(pdf).hexdigest()
            contract.write({
                'pdf_attachment_id': attachment.id,
                'body_hash': hashlib.sha256((contract.body_html or '').encode('utf-8')).hexdigest(),
                'source_hash': pdf_hash,
                'pdf_hash': pdf_hash,
                'state': 'generated',
            })
        return True

    def action_send_for_signature(self):
        for contract in self:
            contract._sync_from_sign_request()
            if contract.sign_oca_request_id and contract.sign_oca_request_id.state in ('0_sent', '1_draft'):
                if contract.sign_oca_request_id.state == '1_draft':
                    contract.sign_oca_request_id.action_send()
                contract.write({'state': 'sent'})
                contract.event_id._sync_ponton_contract_state()
                continue
            if contract.state != 'generated':
                raise UserError(_('Primero genera el PDF del contrato.'))
            event = contract.event_id
            organizer_role, manso_role = contract._get_sign_roles()
            organizer = event.organizer_id
            manso_partner = event._get_ponton_manso_signer()
            if not organizer or not organizer.email:
                raise ValidationError(_('Carga un organizador/productor con email antes de enviar el contrato.'))
            if not manso_partner:
                raise ValidationError(_('Crea el contacto Guido Yamaguchi antes de enviar el contrato.'))
            if not manso_partner.email:
                raise ValidationError(_('Guido Yamaguchi necesita email para recibir la firma online.'))
            if not contract.pdf_attachment_id:
                contract.action_generate_pdf()
            signatory_data = contract._get_signatory_data(organizer_role, manso_role)
            validity_days = event.event_type_id.ponton_contract_validity_days or 10
            expires_at = fields.Datetime.add(fields.Datetime.now(), days=validity_days)

            request_vals = {
                'name': contract.name,
                'template_id': event.event_type_id.ponton_contract_template_id.id or False,
                'record_ref': f'event.event,{event.id}',
                'data': contract.pdf_attachment_id.datas,
                'filename': contract.pdf_attachment_id.name,
                'signatory_data': signatory_data,
                'signer_ids': [
                    (0, 0, {'partner_id': organizer.id, 'role_id': organizer_role.id}),
                    (0, 0, {'partner_id': manso_partner.id, 'role_id': manso_role.id}),
                ],
            }
            request = self.env['sign.oca.request'].create(request_vals)
            request.action_send()
            contract.write({
                'sign_oca_request_id': request.id,
                'state': 'sent',
                'expires_at': expires_at,
            })
            event.write({
                'ponton_contract_id': contract.id,
                'ponton_contract_state': 'sent',
                'ponton_contract_sign_oca_request_id': request.id,
            })
        return True

    def action_mark_obsolete(self):
        self.filtered(lambda contract: contract.state in ('generated', 'sent', 'signed')).write({
            'state': 'obsolete',
        })

    def action_cancel(self):
        for contract in self:
            if contract.sign_oca_request_id and contract.sign_oca_request_id.state != '2_signed':
                contract.sign_oca_request_id.cancel()
            contract.state = 'cancelled'
            contract.event_id._sync_ponton_contract_state()
        return True

    def _sync_from_sign_request(self):
        for contract in self:
            request = contract.sign_oca_request_id
            if not request:
                continue
            vals = {}
            if request.state == '2_signed':
                signed_attachment = contract._ensure_signed_attachment()
                vals.update({
                    'state': 'signed',
                    'signed_at': contract.signed_at or fields.Datetime.now(),
                    'signed_hash': request.current_hash,
                    'signed_attachment_id': signed_attachment.id if signed_attachment else False,
                })
            elif request.state == '3_cancel' and contract.state not in ('signed', 'obsolete'):
                vals['state'] = 'cancelled'
            elif request.state == '0_sent' and contract.state == 'generated':
                vals['state'] = 'sent'
            if vals:
                contract.write(vals)
            contract.event_id._sync_ponton_contract_state()

    def _get_report_context(self):
        self.ensure_one()
        return {
            'contract': self,
            'event': self.event_id,
            'body': Markup(self.body_html or ''),
        }

    def _get_sign_roles(self):
        self.ensure_one()
        event_type = self.event_id.event_type_id
        organizer_role = (
            event_type.ponton_contract_organizer_role_id
            or self.env.ref('ponton_event_contracts.sign_role_event_organizer')
        )
        manso_role = (
            event_type.ponton_contract_manso_role_id
            or self.env.ref('ponton_event_contracts.sign_role_manso')
        )
        return organizer_role, manso_role

    def _get_signatory_data(self, organizer_role, manso_role):
        self.ensure_one()
        template = self.event_id.event_type_id.ponton_contract_template_id
        if template and template.item_ids:
            data = template._get_signatory_data()
            role_ids = {item['role_id'] for item in data.values()}
            expected_role_ids = {organizer_role.id, manso_role.id}
            if not expected_role_ids.issubset(role_ids):
                raise ValidationError(_(
                    'La plantilla OCA Sign debe incluir campos para los roles Organizador y Manso.'
                ))
            extra_roles = role_ids - expected_role_ids
            if extra_roles:
                raise ValidationError(_(
                    'La plantilla OCA Sign del tipo de evento solo puede usar los roles Organizador y Manso.'
                ))
            return data
        return self._default_signatory_data(organizer_role.id, manso_role.id)

    def _default_signatory_data(self, organizer_role_id, manso_role_id):
        self.ensure_one()
        signature_field = self.env.ref('sign_oca.sign_field_signature')
        page = self._get_pdf_page_count()
        return {
            1: {
                'id': 1,
                'field_id': signature_field.id,
                'field_type': 'signature',
                'required': True,
                'name': signature_field.name,
                'role_id': organizer_role_id,
                'page': page,
                'position_x': 10,
                'position_y': 82,
                'width': 30,
                'height': 8,
                'value': False,
                'default_value': signature_field.default_value,
                'placeholder': 'Firma Organizador',
            },
            2: {
                'id': 2,
                'field_id': signature_field.id,
                'field_type': 'signature',
                'required': True,
                'name': signature_field.name,
                'role_id': manso_role_id,
                'page': page,
                'position_x': 60,
                'position_y': 82,
                'width': 30,
                'height': 8,
                'value': False,
                'default_value': signature_field.default_value,
                'placeholder': 'Firma Manso',
            },
        }

    def _get_pdf_page_count(self):
        self.ensure_one()
        if not self.pdf_attachment_id:
            return 1
        try:
            reader = PdfFileReader(BytesIO(b64decode(self.pdf_attachment_id.datas)))
            return max(reader.numPages, 1)
        except Exception as error:
            raise UserError(_('No se pudo leer el PDF del contrato: %s') % error) from error

    def _ensure_signed_attachment(self):
        self.ensure_one()
        request = self.sign_oca_request_id
        if not request or not request.data:
            return self.env['ir.attachment']
        signed_pdf = b64decode(request.data)
        signed_hash = request.current_hash or hashlib.sha1(signed_pdf).hexdigest()
        if self.signed_attachment_id and self.signed_hash == signed_hash:
            return self.signed_attachment_id
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.name} - firmado.pdf',
            'type': 'binary',
            'datas': request.data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.message_post(
            body=_('Contrato firmado adjuntado desde OCA Sign.'),
            attachment_ids=[attachment.id],
        )
        self.event_id.message_post(
            body=_('Contrato de coproduccion firmado.'),
            attachment_ids=[attachment.id],
        )
        return attachment

    @api.model
    def _cron_expire_unsigned_contracts(self):
        expired = self.search([
            ('state', '=', 'sent'),
            ('expires_at', '!=', False),
            ('expires_at', '<', fields.Datetime.now()),
        ])
        for contract in expired:
            if contract.sign_oca_request_id and contract.sign_oca_request_id.state == '0_sent':
                contract.sign_oca_request_id.cancel()
            contract.state = 'expired'
            contract.event_id._sync_ponton_contract_state()
        return True

    @staticmethod
    def _html_value(value):
        return html_escape(value or '')
