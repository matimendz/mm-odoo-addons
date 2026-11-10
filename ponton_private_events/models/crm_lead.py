from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .private_event_config import GUEST_MODE_SELECTION, PRIVATE_EVENT_TYPE_SELECTION


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    ponton_private_event_type = fields.Selection(PRIVATE_EVENT_TYPE_SELECTION, string='Tipo de evento privado')
    ponton_private_tentative_date = fields.Date('Fecha tentativa')
    ponton_private_guest_count = fields.Integer('Invitados estimados')
    ponton_private_guest_mode = fields.Selection(GUEST_MODE_SELECTION, string='Modalidad deseada')
    ponton_private_origin_channel = fields.Selection(
        [
            ('referral', 'Recomendacion'),
            ('instagram', 'Instagram'),
            ('whatsapp', 'WhatsApp'),
            ('web', 'Sitio web'),
            ('meta_ads', 'Meta Ads'),
            ('planner', 'Wedding planner / organizador'),
            ('other', 'Otro'),
        ],
        string='Origen privado',
    )
    ponton_private_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    ponton_private_budget = fields.Monetary('Presupuesto estimado', currency_field='ponton_private_currency_id')
    ponton_private_next_action_date = fields.Date('Proxima accion')
    ponton_private_lost_reason = fields.Char('Motivo perdida privado')
    ponton_private_event_id = fields.Many2one('event.event', string='Evento privado')
    ponton_private_quote_id = fields.Many2one('sale.order', string='Cotizacion privada')

    def action_ponton_create_private_event(self):
        self.ensure_one()
        if self.ponton_private_event_id:
            return self._action_open_private_event()
        if not self.partner_id and not self.contact_name:
            raise ValidationError(_('Carga un contacto antes de crear el evento privado.'))
        partner = self.partner_id or self.env['res.partner'].create({
            'name': self.contact_name or self.name,
            'email': self.email_from,
            'phone': self.phone,
        })
        event_type = self.env['event.type'].search([('ponton_contract_kind', '=', 'private_event')], limit=1)
        operation = self.env.ref('ponton_fudo.analytic_operation_evento_privado', raise_if_not_found=False)
        date_begin, date_end = self._ponton_private_default_event_datetimes()
        event_vals = {
            'name': self.name,
            'organizer_id': partner.id,
            'date_begin': date_begin,
            'date_end': date_end,
            'seats_max': self.ponton_private_guest_count or 50,
            'ponton_private_event_type': self.ponton_private_event_type,
            'ponton_private_guest_mode': self.ponton_private_guest_mode or 'mixed',
            'ponton_private_guaranteed_guests': self.ponton_private_guest_count or 50,
            'ponton_private_commercial_model': self._default_private_commercial_model(),
            'ponton_contract_required': True,
            'ponton_contract_kind': 'private_event',
        }
        if event_type:
            event_vals['event_type_id'] = event_type.id
        if operation:
            event_vals['fudo_operation_analytic_account_id'] = operation.id
        event = self.env['event.event'].create(event_vals)
        self.ponton_private_event_id = event.id
        return self._action_open_private_event()

    def _ponton_private_default_event_datetimes(self):
        self.ensure_one()
        if not self.ponton_private_tentative_date:
            return False, False
        event_date = fields.Date.to_date(self.ponton_private_tentative_date)
        date_begin = datetime.combine(event_date, time(hour=21))
        date_end = datetime.combine(event_date + timedelta(days=1), time(hour=5))
        return date_begin, date_end

    def action_ponton_create_private_quote(self):
        self.ensure_one()
        if not self.ponton_private_event_id:
            self.action_ponton_create_private_event()
        action = self.ponton_private_event_id.action_ponton_generate_private_quote()
        self.ponton_private_quote_id = action.get('res_id')
        self._ponton_private_schedule_followups()
        return action

    def _action_open_private_event(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Evento privado'),
            'res_model': 'event.event',
            'res_id': self.ponton_private_event_id.id,
            'view_mode': 'form',
        }

    def _default_private_commercial_model(self):
        self.ensure_one()
        if self.ponton_private_event_type in ('wedding', 'birthday_50_plus', 'fifteen_high_profile'):
            return 'package_per_person'
        return 'space_fee_plus_minimum_consumption'

    def _ponton_private_schedule_followups(self):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        for lead in self:
            for days, summary in (
                (3, _('Follow-up cotizacion evento privado T+3')),
                (7, _('Follow-up cotizacion evento privado T+7')),
                (15, _('Follow-up cotizacion evento privado T+15')),
            ):
                lead.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=summary,
                    date_deadline=fields.Date.add(fields.Date.context_today(lead), days=days),
                )

    def action_set_won(self, **additional_values):
        result = super().action_set_won(**additional_values)
        for lead in self.filtered(lambda lead: lead.ponton_private_event_type and not lead.ponton_private_event_id):
            lead.action_ponton_create_private_event()
        return result

    def action_set_won_rainbowman(self):
        result = super().action_set_won_rainbowman()
        for lead in self.filtered(lambda lead: lead.ponton_private_event_type and not lead.ponton_private_event_id):
            lead.action_ponton_create_private_event()
        return result
