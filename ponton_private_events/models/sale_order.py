from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .private_event_config import COMMERCIAL_MODEL_SELECTION, QUOTE_BLOCK_SELECTION


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ponton_private_event_id = fields.Many2one('event.event', string='Evento privado')
    ponton_private_quote_version = fields.Integer('Version cotizacion', default=1)
    ponton_private_quote_valid_until = fields.Date('Vigencia cotizacion')
    ponton_private_commercial_model = fields.Selection(COMMERCIAL_MODEL_SELECTION, string='Modelo comercial privado')
    ponton_private_total_usd_reference = fields.Float('Referencia USD')
    ponton_private_deposit_amount = fields.Monetary(
        'Sena 30%',
        compute='_compute_ponton_private_deposit_amount',
        store=True,
        currency_field='currency_id',
    )
    ponton_private_balance_due_date = fields.Date('Vencimiento saldo')

    @api.depends('amount_total')
    def _compute_ponton_private_deposit_amount(self):
        for order in self:
            order.ponton_private_deposit_amount = order.amount_total * 0.30

    def action_ponton_private_confirm_event(self):
        for order in self:
            if not order.ponton_private_event_id:
                raise ValidationError(_('Esta cotizacion no esta vinculada a un evento privado.'))
            order._check_ponton_private_quote_validity()
            event = order.ponton_private_event_id
            order.action_confirm()
            event.write({
                'ponton_private_quote_id': order.id,
                'ponton_private_sale_order_id': order.id,
                'ponton_private_balance_due_date': order.ponton_private_balance_due_date,
            })
            order._ponton_private_schedule_payment_activities()
            if not event.ponton_contract_id:
                event.action_ponton_generate_contract()
        return True

    def _check_ponton_private_quote_validity(self):
        today = fields.Date.context_today(self)
        for order in self:
            if (
                order.ponton_private_quote_valid_until
                and order.ponton_private_quote_valid_until < today
                and not self.env.user.has_group('event.group_event_manager')
            ):
                raise ValidationError(_(
                    'La cotizacion privada vencio el %s. Genera una nueva version o pedi autorizacion manager.'
                ) % fields.Date.to_string(order.ponton_private_quote_valid_until))

    def _ponton_private_build_quote_lines(self):
        for order in self:
            event = order.ponton_private_event_id
            if not event:
                continue
            order.order_line.unlink()
            line_vals = []
            if event.ponton_private_commercial_model == 'package_per_person':
                line_vals += order._ponton_private_package_lines(event)
            else:
                line_vals += order._ponton_private_space_fee_lines(event)
            line_vals += order._ponton_private_condition_lines(event)
            self.env['sale.order.line'].create(line_vals)
            order._compute_ponton_private_usd_reference()

    def _ponton_private_package_lines(self, event):
        package = event.ponton_private_package_id or self.env['ponton.private.event.package'].search([
            ('commercial_model', '=', 'package_per_person'),
            ('active', '=', True),
        ], order='sequence, id', limit=1)
        if package and event.ponton_private_package_id != package:
            event.ponton_private_package_id = package.id
        guests = max(event.ponton_private_guaranteed_guests or event.seats_max or 0, package.minimum_guests if package else 50)
        price = event.ponton_private_package_price_per_person or (package.price_per_person if package else 0.0)
        product = package.product_id if package else self.env.ref(
            'ponton_private_events.product_private_event_package',
            raise_if_not_found=False,
        )
        return [self._ponton_private_line_vals(
            product,
            package.name if package else _('Paquete evento privado'),
            guests,
            price,
            'base',
        )]

    def _ponton_private_space_fee_lines(self, event):
        event._ponton_private_apply_rate()
        product_space = self.env.ref('ponton_private_events.product_private_event_space_fee', raise_if_not_found=False)
        product_minimum = self.env.ref('ponton_private_events.product_private_event_minimum_consumption', raise_if_not_found=False)
        return [
            self._ponton_private_line_vals(product_space, _('Alquiler exclusivo El Ponton'), 1, event.ponton_private_space_fee, 'base'),
            self._ponton_private_line_vals(product_minimum, _('Consumo minimo garantizado'), 1, event.ponton_private_minimum_consumption, 'gastronomy'),
        ]

    def _ponton_private_condition_lines(self, event):
        lines = []
        if event.ponton_private_external_catering_fee:
            product = self.env.ref('ponton_private_events.product_private_event_external_catering', raise_if_not_found=False)
            lines.append(self._ponton_private_line_vals(product, _('Recargo catering externo'), 1, event.ponton_private_external_catering_fee, 'conditions'))
        if event.ponton_private_corkage_total:
            product = self.env.ref('ponton_private_events.product_private_event_corkage', raise_if_not_found=False)
            lines.append(self._ponton_private_line_vals(product, _('Descorche vino / espumante'), event.ponton_private_corkage_bottles, 15000, 'conditions'))
        if event.ponton_private_overtime_amount:
            product = self.env.ref('ponton_private_events.product_private_event_overtime', raise_if_not_found=False)
            lines.append(self._ponton_private_line_vals(product, _('Hora adicional'), event.ponton_private_overtime_hours, event.ponton_private_overtime_amount / event.ponton_private_overtime_hours, 'optional'))
        return lines

    def _ponton_private_line_vals(self, product, name, qty, price_unit, block):
        vals = {
            'order_id': self.id,
            'name': name,
            'product_uom_qty': qty or 1,
            'price_unit': price_unit or 0.0,
            'ponton_private_quote_block': block,
        }
        if product:
            vals['product_id'] = product.id
        return vals

    def _compute_ponton_private_usd_reference(self):
        for order in self:
            order.ponton_private_total_usd_reference = order.amount_total / 1000.0

    def _ponton_private_schedule_payment_activities(self):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        for order in self:
            if order.ponton_private_balance_due_date:
                order.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=_('Confirmar saldo evento privado'),
                    date_deadline=order.ponton_private_balance_due_date,
                )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ponton_private_quote_block = fields.Selection(
        QUOTE_BLOCK_SELECTION,
        string='Bloque cotizacion privada',
        default='base',
    )


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _ponton_private_apply_rate(self):
        for event in self:
            if event.ponton_private_space_fee and event.ponton_private_minimum_consumption:
                continue
            day_type = 'friday_saturday' if event.date_begin and fields.Date.to_date(event.date_begin).weekday() in (4, 5) else 'weekday_sunday'
            rates = self.env['ponton.private.event.rate'].search([
                ('active', '=', True),
                ('season_band', '=', event.ponton_private_season_band),
                ('day_type', '=', day_type),
            ], order='valid_from desc, id desc')
            rate = rates.filtered(lambda rate: rate.matches_event(event))[:1]
            if rate:
                event.ponton_private_space_fee = rate.space_fee
                event.ponton_private_minimum_consumption = rate.minimum_consumption
