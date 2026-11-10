from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html_escape

from .private_event_config import (
    BAR_MODE_SELECTION,
    CATERING_MODE_SELECTION,
    COMMERCIAL_MODEL_SELECTION,
    GUEST_MODE_SELECTION,
    PRIVATE_EVENT_TYPE_SELECTION,
    SEASON_BAND_SELECTION,
)


PRIVATE_CONTRACT_CRITICAL_FIELDS = {
    'date_begin',
    'date_end',
    'seats_max',
    'organizer_id',
    'ponton_private_event_type',
    'ponton_private_commercial_model',
    'ponton_private_package_id',
    'ponton_private_guest_mode',
    'ponton_private_guaranteed_guests',
    'ponton_private_final_guests',
    'ponton_private_season_band',
    'ponton_private_space_fee',
    'ponton_private_minimum_consumption',
    'ponton_private_package_price_per_person',
    'ponton_private_catering_mode',
    'ponton_private_external_catering_fee',
    'ponton_private_corkage_bottles',
    'ponton_private_bar_mode',
    'ponton_private_overtime_hours',
    'ponton_private_quote_id',
    'ponton_private_sale_order_id',
    'ponton_private_balance_due_date',
    'ponton_contract_special_terms',
}


PRIVATE_MANAGER_OVERRIDE_FIELDS = {
    'ponton_private_allow_blackout_override',
    'ponton_private_allow_balance_override',
    'ponton_private_allow_guest_minimum_override',
}

PRIVATE_CONFIRMATION_FIELD_TRIGGERS = {
    'ponton_private_deposit_paid',
    'ponton_private_balance_paid',
    'ponton_private_balance_due_date',
    'ponton_private_allow_balance_override',
    'ponton_contract_id',
    'ponton_contract_state',
}


class EventEvent(models.Model):
    _inherit = 'event.event'

    ponton_contract_kind = fields.Selection(
        selection_add=[('private_event', 'Evento privado')],
        ondelete={'private_event': 'set default'},
    )
    ponton_private_event_type = fields.Selection(PRIVATE_EVENT_TYPE_SELECTION, string='Tipo de evento privado')
    ponton_private_commercial_model = fields.Selection(
        COMMERCIAL_MODEL_SELECTION,
        string='Modelo comercial privado',
    )
    ponton_private_package_id = fields.Many2one('ponton.private.event.package', string='Paquete privado')
    ponton_private_guest_mode = fields.Selection(GUEST_MODE_SELECTION, string='Modalidad invitados')
    ponton_private_guaranteed_guests = fields.Integer('Invitados garantizados')
    ponton_private_final_guests = fields.Integer('Invitados finales')
    ponton_private_season_band = fields.Selection(SEASON_BAND_SELECTION, string='Temporada', default='medium')
    ponton_private_space_fee = fields.Monetary('Alquiler base', currency_field='company_currency_id')
    ponton_private_minimum_consumption = fields.Monetary('Consumo minimo', currency_field='company_currency_id')
    ponton_private_package_price_per_person = fields.Monetary(
        'Precio paquete por persona',
        currency_field='company_currency_id',
    )
    ponton_private_catering_mode = fields.Selection(
        CATERING_MODE_SELECTION,
        string='Comida',
        default='ponton',
    )
    ponton_private_external_catering_fee = fields.Monetary(
        'Recargo catering externo',
        currency_field='company_currency_id',
        compute='_compute_private_amounts',
        store=True,
        readonly=False,
    )
    ponton_private_corkage_bottles = fields.Integer('Botellas descorche')
    ponton_private_corkage_total = fields.Monetary(
        'Total descorche',
        currency_field='company_currency_id',
        compute='_compute_private_amounts',
        store=True,
        readonly=False,
    )
    ponton_private_bar_mode = fields.Selection(BAR_MODE_SELECTION, string='Modalidad barra')
    ponton_private_overtime_hours = fields.Float('Horas extra')
    ponton_private_overtime_amount = fields.Monetary(
        'Total horas extra',
        currency_field='company_currency_id',
        compute='_compute_private_amounts',
        store=True,
        readonly=False,
    )
    ponton_private_spoc_id = fields.Many2one(
        'res.users',
        string='Responsable operativo',
        default=lambda self: self._default_private_spoc_id(),
    )
    ponton_private_quote_id = fields.Many2one('sale.order', string='Cotizacion vigente', readonly=True)
    ponton_private_sale_order_id = fields.Many2one('sale.order', string='Pedido privado', readonly=True)
    ponton_private_deposit_paid = fields.Boolean('Sena ingresada')
    ponton_private_balance_paid = fields.Boolean('Saldo pagado')
    ponton_private_balance_due_date = fields.Date('Vencimiento saldo')
    ponton_private_nps_score = fields.Integer('NPS post-evento')
    ponton_private_allow_blackout_override = fields.Boolean('Autorizar blackout')
    ponton_private_allow_balance_override = fields.Boolean('Autorizar saldo pendiente')
    ponton_private_allow_guest_minimum_override = fields.Boolean('Autorizar minimo pax')
    ponton_private_checklist_item_ids = fields.One2many(
        'ponton.private.event.checklist.item',
        'event_id',
        string='Checklist privado',
    )
    ponton_private_checklist_progress = fields.Float(
        'Checklist completado',
        compute='_compute_private_checklist_progress',
    )
    ponton_private_incident_ids = fields.One2many(
        'ponton.private.event.incident',
        'event_id',
        string='Incidentes',
    )
    ponton_private_incident_count = fields.Integer(compute='_compute_private_incident_count')
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends(
        'ponton_private_space_fee',
        'ponton_private_minimum_consumption',
        'ponton_private_commercial_model',
        'ponton_private_package_id.price_per_person',
        'ponton_private_package_id.minimum_guests',
        'ponton_private_package_price_per_person',
        'ponton_private_guaranteed_guests',
        'ponton_private_catering_mode',
        'ponton_private_corkage_bottles',
        'ponton_private_overtime_hours',
        'ponton_private_quote_id.amount_total',
        'seats_max',
    )
    def _compute_private_amounts(self):
        for event in self:
            contract_base = event.ponton_private_quote_id.amount_total or (
                event.ponton_private_space_fee + event.ponton_private_minimum_consumption
            )
            event.ponton_private_corkage_total = (event.ponton_private_corkage_bottles or 0) * 15000
            event.ponton_private_external_catering_fee = (
                event._ponton_private_external_catering_base() * 0.25
                if event.ponton_private_catering_mode == 'external'
                else 0.0
            )
            event.ponton_private_overtime_amount = (event.ponton_private_overtime_hours or 0.0) * contract_base * 0.10

    def _ponton_private_external_catering_base(self):
        self.ensure_one()
        if self.ponton_private_space_fee:
            return self.ponton_private_space_fee
        if self.ponton_private_commercial_model == 'package_per_person':
            package = self.ponton_private_package_id
            guests = max(
                self.ponton_private_guaranteed_guests or self.seats_max or 0,
                package.minimum_guests if package else 50,
            )
            price = self.ponton_private_package_price_per_person or (package.price_per_person if package else 0.0)
            return guests * price
        if self.ponton_private_quote_id:
            return self.ponton_private_quote_id.amount_untaxed
        return self.ponton_private_minimum_consumption

    @api.depends('ponton_private_checklist_item_ids.done')
    def _compute_private_checklist_progress(self):
        for event in self:
            total = len(event.ponton_private_checklist_item_ids)
            done = len(event.ponton_private_checklist_item_ids.filtered('done'))
            event.ponton_private_checklist_progress = (done / total * 100.0) if total else 0.0

    @api.depends('ponton_private_incident_ids')
    def _compute_private_incident_count(self):
        for event in self:
            event.ponton_private_incident_count = len(event.ponton_private_incident_ids)

    @api.model
    def _default_private_spoc_id(self):
        partner = self.env['res.partner'].search([('name', 'ilike', 'Fabian')], limit=1)
        user = self.env['res.users'].search([('partner_id', '=', partner.id)], limit=1) if partner else False
        return user.id if user else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_private_override_permissions(vals)
            if self._vals_are_private(vals):
                self._default_private_event_values(vals)
        events = super().create(vals_list)
        for event in events.filtered('ponton_private_commercial_model'):
            event._check_private_event_constraints()
        return events

    def write(self, vals):
        self._check_private_override_permissions(vals)
        private_critical_update = PRIVATE_CONTRACT_CRITICAL_FIELDS.intersection(vals)
        if private_critical_update:
            self._check_ponton_contract_critical_update_allowed(vals)
        private_events = self.filtered('ponton_private_commercial_model')
        if private_events and 'stage_id' in vals:
            target_stage = self.env['event.stage'].browse(vals['stage_id'])
            private_events._check_private_event_confirmation(target_stage=target_stage)
            private_events._check_private_finalization(target_stage=target_stage)
        result = super().write(vals)
        if private_events and (
            private_critical_update
            or 'fudo_operation_analytic_account_id' in vals
            or 'active' in vals
            or 'stage_id' in vals
        ):
            private_events._check_private_event_constraints()
        if private_critical_update:
            private_events._mark_signed_contracts_obsolete()
        if private_events and PRIVATE_CONFIRMATION_FIELD_TRIGGERS.intersection(vals):
            private_events._check_private_event_confirmation()
        return result

    def action_ponton_generate_contract(self):
        private_events = self.filtered(lambda event: event.ponton_contract_kind == 'private_event')
        regular_events = self - private_events
        result = True
        if regular_events:
            result = super(EventEvent, regular_events).action_ponton_generate_contract()
        for event in private_events:
            if not event.ponton_contract_required:
                raise ValidationError(_('Este evento no requiere contrato.'))
            event._ensure_private_contract_basics()
            active_contract = event.ponton_contract_id
            if active_contract and active_contract.state in ('signed', 'sent'):
                raise ValidationError(_(
                    'El contrato actual ya fue enviado o firmado. Genera una nueva version si necesitas modificarlo.'
                ))
            version = len(event.ponton_contract_ids) + 1
            body_html = event._render_private_contract_html()
            contract = self.env['ponton.event.contract'].create({
                'name': _('Contrato evento privado - %s - v%s') % (event.display_name, version),
                'event_id': event.id,
                'version': version,
                'body_html': body_html,
                'body_hash': False,
                'state': 'draft',
            })
            contract.action_generate_pdf()
            event.write({
                'ponton_contract_id': contract.id,
                'ponton_contract_state': 'generated',
            })
        return result

    def action_ponton_generate_private_quote(self):
        self.ensure_one()
        if not self.ponton_private_commercial_model:
            raise ValidationError(_('Selecciona el modelo comercial privado antes de cotizar.'))
        if not self.organizer_id:
            raise ValidationError(_('Carga el cliente/organizador antes de cotizar.'))
        SaleOrder = self.env['sale.order']
        version = SaleOrder.search_count([('ponton_private_event_id', '=', self.id)]) + 1
        order = SaleOrder.create({
            'partner_id': self.organizer_id.id,
            'origin': self.name,
            'ponton_private_event_id': self.id,
            'ponton_private_quote_version': version,
            'ponton_private_commercial_model': self.ponton_private_commercial_model,
            'ponton_private_quote_valid_until': fields.Date.add(fields.Date.context_today(self), days=7),
            'ponton_private_balance_due_date': self._default_private_balance_due_date(),
        })
        order._ponton_private_build_quote_lines()
        self.write({
            'ponton_private_quote_id': order.id,
            'ponton_private_deposit_paid': False,
            'ponton_private_balance_due_date': order.ponton_private_balance_due_date,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cotizacion evento privado'),
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
        }

    def action_ponton_confirm_private_event(self):
        for event in self:
            event._check_private_event_confirmation()
        return True

    def _check_ponton_contract_confirmation(self):
        private_events = self.filtered(lambda event: event.ponton_contract_kind == 'private_event')
        regular_events = self - private_events
        if regular_events:
            super(EventEvent, regular_events)._check_ponton_contract_confirmation()
        for event in private_events:
            if (
                event.ponton_contract_required
                and event.stage_id.is_contract_confirmed_stage
                and not event._has_signed_ponton_contract()
            ):
                raise ValidationError(_('No se puede confirmar un evento privado sin contrato firmado online.'))

    def action_ponton_generate_private_checklist(self):
        template = self.env.ref(
            'ponton_private_events.private_event_checklist_template_default',
            raise_if_not_found=False,
        )
        for event in self:
            if event.ponton_private_checklist_item_ids:
                continue
            items = template.item_ids if template else self.env['ponton.private.event.checklist.item']
            vals_list = []
            for item in items:
                vals_list.append({
                    'name': item.name,
                    'sequence': item.sequence,
                    'stage': item.stage,
                    'is_critical': item.is_critical,
                    'event_id': event.id,
                    'responsible_id': event.ponton_private_spoc_id.id or False,
                })
            if vals_list:
                self.env['ponton.private.event.checklist.item'].create(vals_list)
        return True

    def action_view_private_quote(self):
        self.ensure_one()
        if not self.ponton_private_quote_id:
            return self.action_ponton_generate_private_quote()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cotizacion evento privado'),
            'res_model': 'sale.order',
            'res_id': self.ponton_private_quote_id.id,
            'view_mode': 'form',
        }

    def action_view_private_incidents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Incidentes'),
            'res_model': 'ponton.private.event.incident',
            'view_mode': 'list,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id},
        }

    def _check_private_override_permissions(self, vals):
        if (
            PRIVATE_MANAGER_OVERRIDE_FIELDS.intersection(vals)
            and any(vals.get(field) for field in PRIVATE_MANAGER_OVERRIDE_FIELDS)
            and not self.env.user.has_group('event.group_event_manager')
        ):
            raise ValidationError(_('Solo un manager de eventos puede autorizar excepciones de evento privado.'))

    def _vals_are_private(self, vals):
        if vals.get('ponton_private_commercial_model'):
            return True
        operation_id = vals.get('fudo_operation_analytic_account_id')
        if operation_id:
            operation = self.env['account.analytic.account'].browse(operation_id)
            return operation == self.env.ref('ponton_fudo.analytic_operation_evento_privado', raise_if_not_found=False)
        return False

    def _default_private_event_values(self, vals):
        operation = self.env.ref('ponton_fudo.analytic_operation_evento_privado', raise_if_not_found=False)
        event_type = self.env.ref('ponton_private_events.event_type_private_event', raise_if_not_found=False)
        if event_type:
            vals.setdefault('event_type_id', event_type.id)
        if operation:
            vals.setdefault('fudo_operation_analytic_account_id', operation.id)
        if not vals.get('fudo_event_analytic_account_id'):
            analytic = self._create_private_event_analytic_account(vals)
            if analytic:
                vals['fudo_event_analytic_account_id'] = analytic.id
        vals.setdefault('ponton_contract_required', True)
        vals.setdefault('ponton_contract_kind', 'private_event')
        vals.setdefault('ponton_private_guaranteed_guests', vals.get('seats_max') or 50)
        vals.setdefault('ponton_private_guest_mode', 'mixed')
        vals.setdefault('ponton_private_catering_mode', 'ponton')
        vals.setdefault('ponton_private_bar_mode', 'organizer_account')
        vals.setdefault('ponton_private_balance_due_date', self._default_private_balance_due_date(vals))
        if not vals.get('stage_id'):
            stage = self._default_private_stage_id()
            if stage:
                vals['stage_id'] = stage.id

    def _default_private_stage_id(self):
        preferred = self.env.ref('ponton_event.event_stage_adjustment', raise_if_not_found=False)
        if preferred and not preferred.is_contract_confirmed_stage:
            return preferred
        return self.env['event.stage'].search([
            ('name', 'not in', ['Finalizado', 'Cancelado']),
            ('is_contract_confirmed_stage', '=', False),
            ('fold', '=', False),
        ], order='sequence, id', limit=1)

    def _create_private_event_analytic_account(self, vals):
        plan = self.env.ref('ponton_fudo.analytic_plan_eventos', raise_if_not_found=False)
        if not plan:
            return False
        return self.env['account.analytic.account'].create({
            'name': vals.get('name') or _('Evento privado'),
            'plan_id': plan.id,
        })

    def _default_private_balance_due_date(self, vals=None):
        date_begin = vals.get('date_begin') if vals else self.date_begin
        if date_begin:
            return fields.Date.subtract(fields.Date.to_date(date_begin), days=7)
        return fields.Date.add(fields.Date.context_today(self), days=7)

    def _check_private_event_constraints(self):
        private_operation = self.env.ref('ponton_fudo.analytic_operation_evento_privado', raise_if_not_found=False)
        for event in self:
            missing = []
            if event.active and private_operation and event.fudo_operation_analytic_account_id != private_operation:
                missing.append(_('Tipo de operacion Evento Privado'))
            if event.ponton_private_guaranteed_guests < 50 and not event.ponton_private_allow_guest_minimum_override:
                missing.append(_('Minimo de 50 invitados garantizados o autorizacion manager'))
            blackout = event._get_private_event_blackout()
            if blackout and blackout.blocking:
                if event.ponton_private_allow_blackout_override and not blackout.allow_manager_override:
                    missing.append(_('Fecha blackout sin autorizacion posible: %s') % blackout.display_name)
                elif not event.ponton_private_allow_blackout_override:
                    missing.append(_('Fecha blackout: %s') % blackout.display_name)
            if missing:
                raise ValidationError(_('Evento privado incompleto:\n- %s') % '\n- '.join(missing))

    def _check_private_event_confirmation(self, target_stage=None):
        for event in self:
            stage = target_stage or event.stage_id
            if not event.ponton_private_commercial_model or not stage.is_contract_confirmed_stage:
                continue
            missing = []
            if not event._has_signed_ponton_contract():
                missing.append(_('Contrato firmado online'))
            if not event.ponton_private_deposit_paid:
                missing.append(_('Sena ingresada'))
            if (
                event.ponton_private_balance_due_date
                and event.ponton_private_balance_due_date <= fields.Date.context_today(event)
                and not event.ponton_private_balance_paid
                and not event.ponton_private_allow_balance_override
            ):
                missing.append(_('Saldo pagado o autorizacion de saldo pendiente'))
            if missing:
                raise ValidationError(_('No se puede confirmar el evento privado. Falta:\n- %s') % '\n- '.join(missing))

    def _check_private_finalization(self, target_stage=None):
        for event in self:
            stage = target_stage or event.stage_id
            if not event._is_private_final_stage(stage):
                continue
            critical_open = event.ponton_private_checklist_item_ids.filtered(
                lambda item: item.is_critical and not item.done
            )
            if critical_open:
                raise ValidationError(_('No se puede finalizar con checklist critico pendiente.'))

    def _is_private_final_stage(self, stage):
        self.ensure_one()
        final_stage = self.env.ref('ponton_event.event_stage_done', raise_if_not_found=False)
        return bool(
            stage
            and (
                stage == final_stage
                or getattr(stage, 'pipe_end', False)
                or stage.name == 'Finalizado'
            )
        )

    def _ensure_private_contract_basics(self):
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
            if not (event.ponton_private_guaranteed_guests or event.seats_max):
                missing.append(_('Invitados garantizados o asistentes estimados'))
            if not event.ponton_private_quote_id:
                missing.append(_('Cotizacion vigente'))
            if not event.ponton_private_commercial_model:
                missing.append(_('Modelo comercial privado'))
            if not event.ponton_private_guest_mode:
                missing.append(_('Modalidad de invitados'))
            if missing:
                raise ValidationError(_('No se puede generar el contrato privado. Completa:\n- %s') % '\n- '.join(missing))
            if event.ponton_contract_manso_partner_id != manso_partner:
                event.ponton_contract_manso_partner_id = manso_partner.id

    def _get_private_event_blackout(self):
        self.ensure_one()
        if not self.date_begin:
            return self.env['ponton.private.event.blackout']
        return self.env['ponton.private.event.blackout'].search([
            ('date', '=', fields.Date.to_date(self.date_begin)),
        ], limit=1)

    def _render_ponton_contract_html(self):
        self.ensure_one()
        if self.ponton_contract_kind == 'private_event':
            return self._render_private_contract_html()
        return super()._render_ponton_contract_html()

    def _render_private_contract_html(self):
        self.ensure_one()
        return '\n'.join([
            str(self._render_private_contract_summary()),
            str(self._render_private_contract_terms()),
            str(self._render_private_contract_annex()),
            str(Markup('<h2>Clausulas especiales</h2>%s') % Markup(self.ponton_contract_special_terms or '')),
        ])

    def _render_private_contract_summary(self):
        self.ensure_one()
        return Markup(
            '<h1>Contrato evento privado</h1>'
            '<table class="ponton-contract-summary">'
            '<tr><th>Evento</th><td>{event_name}</td></tr>'
            '<tr><th>Cliente / organizador</th><td>{organizer}</td></tr>'
            '<tr><th>Fecha y horario</th><td>{date_begin} - {date_end}</td></tr>'
            '<tr><th>Invitados garantizados</th><td>{guests}</td></tr>'
            '<tr><th>Modelo comercial</th><td>{model}</td></tr>'
            '<tr><th>Cotizacion</th><td>{quote}</td></tr>'
            '</table>'
        ).format(
            event_name=html_escape(self.ponton_contract_event_name or self.name or ''),
            organizer=html_escape(self.organizer_id.display_name or ''),
            date_begin=html_escape(fields.Datetime.to_string(self.date_begin) if self.date_begin else ''),
            date_end=html_escape(fields.Datetime.to_string(self.date_end) if self.date_end else ''),
            guests=self.ponton_private_guaranteed_guests or self.seats_max or 0,
            model=html_escape(dict(COMMERCIAL_MODEL_SELECTION).get(self.ponton_private_commercial_model, '')),
            quote=html_escape(self.ponton_private_quote_id.name or ''),
        )

    def _render_private_contract_terms(self):
        return Markup(
            '<h2>Condiciones generales</h2>'
            '<ul>'
            '<li>Manso SRL otorga el uso exclusivo de El Ponton para el evento indicado.</li>'
            '<li>La duracion base es de 8 a 10 horas. Cada hora adicional se cobra al 10% del contrato.</li>'
            '<li>La fecha queda reservada solo con contrato firmado y sena del 30% ingresada.</li>'
            '<li>El saldo debe abonarse 7 dias antes del evento.</li>'
            '<li>La bebida es provista exclusivamente por El Ponton. El descorche declarado se cobra por botella.</li>'
            '<li>El catering externo tiene recargo del 25% sobre el alquiler y responsabilidad sanitaria del cliente.</li>'
            '<li>El cliente responde por danos a instalaciones, mobiliario o equipamiento durante el evento.</li>'
            '<li>Musica a volumen pleno hasta las 05:00, sujeto al Codigo de Nocturnidad de Posadas.</li>'
            '<li>SADAIC / AADI-CAPIF es gestionado por El Ponton.</li>'
            '<li>Menores admitidos con adulto responsable. No se sirve alcohol a menores.</li>'
            '<li>El Ponton puede expulsar invitados ante violencia, acoso o consumo problematico.</li>'
            '<li>Acceso de proveedores de 10:00 a 06:00, identificados previamente.</li>'
            '</ul>'
        )

    def _render_private_contract_annex(self):
        self.ensure_one()
        quote = self.ponton_private_quote_id
        rows = []
        if quote:
            for line in quote.order_line.filtered(lambda line: not line.display_type):
                rows.append(Markup('<tr><td>{name}</td><td>{qty}</td><td>{subtotal}</td></tr>').format(
                    name=html_escape(line.name),
                    qty=line.product_uom_qty,
                    subtotal=line.price_subtotal,
                ))
        return Markup(
            '<h2>Anexo variable economico</h2>'
            '<p>Total cotizado: {total}</p>'
            '<p>Sena 30%: {deposit}</p>'
            '<p>Vencimiento saldo: {balance_due}</p>'
            '<table class="ponton-contract-summary"><tr><th>Concepto</th><th>Cantidad</th><th>Subtotal</th></tr>{rows}</table>'
        ).format(
            total=quote.amount_total if quote else 0.0,
            deposit=quote.ponton_private_deposit_amount if quote else 0.0,
            balance_due=html_escape(fields.Date.to_string(self.ponton_private_balance_due_date) if self.ponton_private_balance_due_date else ''),
            rows=Markup('').join(rows),
        )


class EventType(models.Model):
    _inherit = 'event.type'

    ponton_contract_kind = fields.Selection(
        selection_add=[('private_event', 'Evento privado')],
        ondelete={'private_event': 'set default'},
    )
