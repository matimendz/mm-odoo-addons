import hashlib

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html_escape


CONTRACT_CRITICAL_FIELDS = {
    'name',
    'date_begin',
    'date_end',
    'seats_max',
    'ponton_contract_event_name',
    'organizer_id',
    'ponton_contract_organizer_id',
    'ponton_contract_organizer_email',
    'ponton_contract_organizer_phone',
    'ponton_contract_organizer_document',
    'ponton_contract_guest_count',
    'ponton_contract_final_capacity',
    'ponton_contract_manso_guest_passes',
    'ponton_contract_access_filter_note',
    'ponton_contract_reservation_note',
    'ponton_contract_ponton_income',
    'ponton_contract_ponton_expense',
    'ponton_contract_organizer_income',
    'ponton_contract_organizer_expense',
    'ponton_contract_special_terms',
}


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _default_ponton_manso_partner_id(self):
        return self._get_ponton_manso_signer()

    ponton_contract_required = fields.Boolean(
        string='Requiere contrato',
        compute='_compute_ponton_contract_required',
        store=True,
        readonly=True,
    )
    ponton_contract_kind = fields.Selection(
        [('coproduction', 'Coproduccion')],
        string='Tipo de contrato',
        default='coproduction',
    )
    ponton_contract_event_name = fields.Char('Nombre contractual')
    ponton_contract_organizer_id = fields.Many2one(
        related='organizer_id',
        string='Organizador',
        readonly=False,
        store=True,
    )
    ponton_contract_organizer_email = fields.Char(
        related='organizer_id.email',
        string='Email organizador',
        readonly=False,
        store=True,
    )
    ponton_contract_organizer_phone = fields.Char(
        related='organizer_id.phone',
        string='Telefono organizador',
        readonly=False,
        store=True,
    )
    ponton_contract_organizer_document = fields.Char(
        related='organizer_id.vat',
        string='Documento/CUIT organizador',
        readonly=False,
        store=True,
    )
    ponton_contract_manso_partner_id = fields.Many2one(
        'res.partner',
        string='Firmante Manso',
        default=_default_ponton_manso_partner_id,
    )
    ponton_contract_guest_count = fields.Integer('Asistentes contrato')
    ponton_contract_final_capacity = fields.Integer('Capacidad final')
    ponton_contract_manso_guest_passes = fields.Integer('Ingresos sin cargo Manso', default=15)
    ponton_contract_capacity_lock_days = fields.Integer('Dias cierre capacidad', default=10)
    ponton_contract_supplier_deadline_hours = fields.Integer('Horas limite proveedores', default=48)
    ponton_contract_access_filter_note = fields.Text('Nota de ingresos/filtro')
    ponton_contract_reservation_note = fields.Text('Nota de reservas')
    ponton_contract_ponton_income = fields.Text(
        'Ingresos El Ponton/Manso',
        default='Ingresos de barra y cocina.\nIngresos de estacionamiento.',
    )
    ponton_contract_ponton_expense = fields.Text(
        'Gastos El Ponton/Manso',
        default='Instalaciones.\nHabilitacion eventual municipal.\nPolicia.\nImpuestos.\n'
                'Seguridad privada (NO filtros de VIP, camarote).\n'
                'Personal de barra, cocina y mozos.\nLimpieza.\n'
                'Demas gastos de adecuacion del espacio, como barras extra, banos quimicos o carpa por lluvia.',
    )
    ponton_contract_organizer_income = fields.Text(
        'Ingresos organizador',
        default='Ingresos de entradas.',
    )
    ponton_contract_organizer_expense = fields.Text(
        'Gastos organizador',
        default='Tecnica, sonido e iluminacion.\nEscenarios, vallas, VIPs y camarotes.\n'
                'DJs, VJs y artistas.\nConsolas e instrumentos.\nDecoracion y cotillon.\n'
                'Comunicacion.\nFotografia y audiovisual.\nPortero y filtros para VIPs/camarotes.\n'
                'Comisiones de venta de entradas y relaciones publicas.\nGastos por acciones de marketing.\n'
                'Demas gastos de produccion.',
    )
    ponton_contract_special_terms = fields.Html('Clausulas especiales')
    ponton_contract_state = fields.Selection(
        [
            ('none', 'Sin contrato'),
            ('draft', 'Borrador'),
            ('generated', 'Generado'),
            ('sent', 'Enviado'),
            ('signed', 'Firmado'),
            ('cancelled', 'Cancelado'),
            ('expired', 'Vencido'),
            ('obsolete', 'Obsoleto'),
        ],
        default='none',
        readonly=True,
        tracking=True,
    )
    ponton_contract_id = fields.Many2one('ponton.event.contract', string='Contrato vigente', readonly=True)
    ponton_contract_ids = fields.One2many('ponton.event.contract', 'event_id', string='Contratos')
    ponton_contract_count = fields.Integer(compute='_compute_ponton_contract_count')
    ponton_contract_sign_oca_request_id = fields.Many2one(
        'sign.oca.request',
        string='Solicitud OCA Sign',
        readonly=True,
    )
    ponton_contract_signed_at = fields.Datetime(
        related='ponton_contract_id.signed_at',
        string='Firmado el',
        readonly=True,
    )

    @api.depends(
        'event_type_id',
        'event_type_id.ponton_contract_required',
        'fudo_operation_analytic_account_id',
        'fudo_operation_analytic_account_id.ponton_contract_required_for_events',
    )
    def _compute_ponton_contract_required(self):
        for event in self:
            event.ponton_contract_required = bool(
                (
                    event.event_type_id
                    and event.event_type_id.ponton_contract_required
                )
                or (
                    event.fudo_operation_analytic_account_id
                    and event.fudo_operation_analytic_account_id.ponton_contract_required_for_events
                )
            )

    @api.depends('ponton_contract_ids')
    def _compute_ponton_contract_count(self):
        for event in self:
            event.ponton_contract_count = len(event.ponton_contract_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._default_contract_values(vals)
        events = super().create(vals_list)
        for event, vals in zip(events, vals_list):
            if 'stage_id' in vals:
                event._check_ponton_stage_requirements()
        return events

    def write(self, vals):
        if 'event_type_id' in vals:
            self._default_contract_values(vals)
        critical_update = CONTRACT_CRITICAL_FIELDS.intersection(vals)
        if critical_update:
            self._check_ponton_contract_critical_update_allowed(vals)
        result = super().write(vals)
        if 'stage_id' in vals:
            self._check_ponton_stage_requirements()
        if critical_update:
            self._mark_signed_contracts_obsolete()
        if {'ponton_contract_id', 'ponton_contract_state'}.isdisjoint(vals):
            self._sync_ponton_contract_state()
        if (
            'stage_id' in vals
            or 'event_type_id' in vals
            or 'fudo_operation_analytic_account_id' in vals
            or 'ponton_contract_required' in vals
            or 'ponton_contract_id' in vals
            or critical_update
        ):
            self._check_ponton_contract_confirmation()
        return result

    def action_ponton_generate_contract(self):
        Contract = self.env['ponton.event.contract']
        for event in self:
            if not event.ponton_contract_required:
                raise ValidationError(_('Este evento no requiere contrato.'))
            event._ensure_contract_basics()
            active_contract = event.ponton_contract_id
            if active_contract and active_contract.state in ('signed', 'sent'):
                raise ValidationError(_('El contrato actual ya fue enviado o firmado. Genera una nueva version si necesitas modificarlo.'))
            version = len(event.ponton_contract_ids) + 1
            body_html = event._render_ponton_contract_html()
            body_hash = hashlib.sha256(body_html.encode('utf-8')).hexdigest()
            contract = Contract.create({
                'name': _('Contrato coproduccion - %s - v%s') % (event.display_name, version),
                'event_id': event.id,
                'version': version,
                'body_html': body_html,
                'body_hash': body_hash,
                'state': 'draft',
            })
            contract.action_generate_pdf()
            event.write({
                'ponton_contract_id': contract.id,
                'ponton_contract_state': 'generated',
            })
        return True

    def action_ponton_send_contract(self):
        for event in self:
            contract = event.ponton_contract_id
            if not contract:
                event.action_ponton_generate_contract()
                contract = event.ponton_contract_id
            contract.action_send_for_signature()
        return True

    def action_ponton_confirm_event(self):
        self._check_ponton_contract_confirmation()
        return True

    def action_view_ponton_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contratos'),
            'res_model': 'ponton.event.contract',
            'view_mode': 'list,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id},
        }

    def _default_contract_values(self, vals):
        if 'event_type_id' in vals and not vals.get('event_type_id'):
            vals.setdefault('ponton_contract_required', False)
            vals.setdefault('ponton_contract_kind', 'coproduction')
        elif vals.get('event_type_id'):
            event_type = self.env['event.type'].browse(vals['event_type_id'])
            vals.setdefault('ponton_contract_required', event_type.ponton_contract_required)
            vals.setdefault('ponton_contract_kind', event_type.ponton_contract_kind)
            manso_partner = self._get_ponton_manso_signer() or event_type.ponton_contract_manso_partner_id
            if manso_partner:
                vals.setdefault('ponton_contract_manso_partner_id', manso_partner.id)

    def _ensure_contract_basics(self):
        for event in self:
            manso_partner = event._get_ponton_manso_signer()
            missing = []
            if not event.event_type_id:
                missing.append(_('Tipo de evento'))
            if not event.fudo_operation_analytic_account_id:
                missing.append(_('Tipo de operacion'))
            if not event.fudo_event_analytic_account_id:
                missing.append(_('Cuenta analitica del evento'))
            if not event.organizer_id:
                missing.append(_('Organizador'))
            else:
                if not event.organizer_id.email:
                    missing.append(_('Email del organizador'))
                if not event.organizer_id.phone:
                    missing.append(_('Telefono del organizador'))
                if not event.organizer_id.vat:
                    missing.append(_('Documento/CUIT del organizador'))
            if not manso_partner:
                missing.append(_('Contacto firmante Manso: Guido Yamaguchi'))
            elif not manso_partner.email:
                missing.append(_('Email de Guido Yamaguchi'))
            if not event.name:
                missing.append(_('Nombre del evento'))
            if not event.date_begin:
                missing.append(_('Fecha/hora de inicio'))
            if not event.date_end:
                missing.append(_('Fecha/hora de fin'))
            if not (event.ponton_contract_guest_count or event.seats_max):
                missing.append(_('Asistentes estimados o asistentes contrato'))
            if not (event.ponton_contract_final_capacity or event.seats_max):
                missing.append(_('Capacidad final o asistentes estimados'))
            if not event.ponton_contract_ponton_income:
                missing.append(_('Ingresos El Ponton/Manso'))
            if not event.ponton_contract_ponton_expense:
                missing.append(_('Gastos El Ponton/Manso'))
            if not event.ponton_contract_organizer_income:
                missing.append(_('Ingresos organizador'))
            if not event.ponton_contract_organizer_expense:
                missing.append(_('Gastos organizador'))
            if missing:
                raise ValidationError(_(
                    'No se puede generar el contrato. Completa primero estos datos:\n- %s'
                ) % '\n- '.join(missing))
            if event.ponton_contract_manso_partner_id != manso_partner:
                event.ponton_contract_manso_partner_id = manso_partner.id

    def _get_ponton_manso_signer(self):
        Partner = self.env['res.partner'].sudo()
        return (
            Partner.search([('email', '=ilike', 'guidoyamaguchi@gmail.com')], limit=1)
            or Partner.search([('name', '=ilike', 'Guido Yamaguchi')], limit=1)
        )

    def _check_ponton_stage_requirements(self):
        for event in self:
            if not event.event_type_id:
                raise ValidationError(_(
                    'Selecciona el tipo de evento antes de moverlo de etapa. '
                    'El tipo de evento y el tipo de operacion definen si el evento requiere contrato.'
                ))

    def _check_ponton_contract_critical_update_allowed(self, vals):
        target_stage = self.env['event.stage'].browse(vals['stage_id']) if vals.get('stage_id') else False
        for event in self:
            stage = target_stage or event.stage_id
            if (
                stage.is_contract_confirmed_stage
                and event.ponton_contract_required
                and event._has_signed_ponton_contract()
            ):
                raise ValidationError(_(
                    'No se pueden modificar datos contractuales criticos en un evento confirmado. '
                    'Primero movelo a una etapa no confirmada y luego genera una nueva version del contrato.'
                ))

    def _check_ponton_contract_confirmation(self):
        for event in self:
            if (
                event.ponton_contract_required
                and event.stage_id.is_contract_confirmed_stage
                and not event._has_signed_ponton_contract()
            ):
                raise ValidationError(
                    _('No se puede confirmar un evento de coproduccion sin contrato firmado online.')
                )

    def _has_signed_ponton_contract(self):
        self.ensure_one()
        contract = self.ponton_contract_id
        return bool(
            contract
            and contract.state == 'signed'
            and (
                not contract.sign_oca_request_id
                or contract.sign_oca_request_id.state == '2_signed'
            )
        )

    def _mark_signed_contracts_obsolete(self):
        for event in self:
            contracts = event.ponton_contract_ids.filtered(
                lambda contract: contract.state in ('generated', 'sent', 'signed')
            )
            if contracts:
                contracts.write({'state': 'obsolete'})
                super(EventEvent, event).write({'ponton_contract_state': 'obsolete'})

    def _sync_ponton_contract_state(self):
        for event in self:
            contract = event.ponton_contract_id
            state = contract.state if contract else 'none'
            vals = {'ponton_contract_state': state}
            if contract and contract.sign_oca_request_id:
                vals['ponton_contract_sign_oca_request_id'] = contract.sign_oca_request_id.id
            if (
                event.ponton_contract_state != state
                or (
                    contract
                    and contract.sign_oca_request_id
                    and event.ponton_contract_sign_oca_request_id != contract.sign_oca_request_id
                )
            ):
                super(EventEvent, event).write(vals)

    def _render_ponton_contract_html(self):
        self.ensure_one()
        clauses = self._get_ponton_contract_clauses()
        sections = []
        sections.append(self._render_contract_summary())
        sections.append(self._render_split_section())
        for clause in clauses:
            sections.append(clause._render_for_event(self))
        if self.ponton_contract_special_terms:
            sections.append('<h2>Clausulas especiales</h2>%s' % self.ponton_contract_special_terms)
        return '\n'.join(sections)

    def _get_ponton_contract_clauses(self):
        self.ensure_one()
        Clause = self.env['ponton.event.contract.clause']
        domain = [
            ('active', '=', True),
            '|',
            ('event_id', '=', False),
            ('event_id', '=', self.id),
        ]
        clauses = Clause.search(domain)
        if self.event_type_id:
            clauses = clauses.filtered(
                lambda clause: not clause.event_type_ids or self.event_type_id in clause.event_type_ids
            )
        return clauses

    def _render_contract_summary(self):
        self.ensure_one()
        event_name = html_escape(self.ponton_contract_event_name or self.name or '')
        organizer = html_escape(
            self.organizer_id.display_name
            or self.ponton_organizer_text
            or ''
        )
        date_begin = html_escape(fields.Datetime.to_string(self.date_begin) if self.date_begin else '')
        date_end = html_escape(fields.Datetime.to_string(self.date_end) if self.date_end else '')
        guests = self.ponton_contract_guest_count or self.seats_max or 0
        return Markup(
            '<h1>Propuesta coproduccion</h1>'
            '<table class="ponton-contract-summary">'
            '<tr><th>Evento</th><td>{event_name}</td></tr>'
            '<tr><th>Organizador</th><td>{organizer}</td></tr>'
            '<tr><th>Fecha y horario</th><td>{date_begin} - {date_end}</td></tr>'
            '<tr><th>Asistentes</th><td>{guests}</td></tr>'
            '</table>'
        ).format(event_name=event_name, organizer=organizer, date_begin=date_begin, date_end=date_end, guests=guests)

    def _render_split_section(self):
        self.ensure_one()
        return Markup(
            '<h2>Division de gastos e ingresos</h2>'
            '<div class="ponton-contract-split">'
            '<h3>El Ponton / Manso</h3>'
            '<h4>Ingresos</h4>{ponton_income}'
            '<h4>Gastos</h4>{ponton_expense}'
            '<h3>Organizador</h3>'
            '<h4>Ingresos</h4>{organizer_income}'
            '<h4>Gastos</h4>{organizer_expense}'
            '</div>'
        ).format(
            ponton_income=self._text_to_html_list(self.ponton_contract_ponton_income),
            ponton_expense=self._text_to_html_list(self.ponton_contract_ponton_expense),
            organizer_income=self._text_to_html_list(self.ponton_contract_organizer_income),
            organizer_expense=self._text_to_html_list(self.ponton_contract_organizer_expense),
        )

    @staticmethod
    def _text_to_html_list(text):
        items = [line.strip() for line in (text or '').splitlines() if line.strip()]
        if not items:
            return Markup('<p>-</p>')
        return Markup('<ul>%s</ul>') % Markup('').join(
            Markup('<li>%s</li>') % html_escape(item)
            for item in items
        )
