from odoo import api, fields, models
from odoo.exceptions import ValidationError

FUDO_EVENT_TYPE_SELECTION = [
    ('evento_propio', 'Evento Propio'),
    ('coproduccion', 'Coproducción'),
    ('evento_privado', 'Evento Privado'),
]


class EventEvent(models.Model):
    _inherit = 'event.event'

    fudo_sale_type = fields.Selection(
        FUDO_EVENT_TYPE_SELECTION,
        string='Tipo Fudo (legacy)',
        help='Campo legado. La clasificación contable Fudo ahora usa las cuentas '
             'analíticas del evento y del tipo de operación.',
    )
    fudo_event_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta analítica del evento',
        domain="[('plan_id.name', '=', 'Eventos')]",
        index=True,
        help='Cuenta analítica nativa usada para imputar ventas y gastos de este evento.',
    )
    fudo_operation_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tipo de operación',
        domain="[('plan_id.name', '=', 'Tipo de Operación')]",
        index=True,
        help='Cuenta del plan Tipo de Operación usada para clasificar este evento.',
    )

    @api.constrains('active', 'fudo_event_analytic_account_id', 'fudo_operation_analytic_account_id')
    def _check_fudo_required_analytics(self):
        for event in self:
            if event.active and (
                not event.fudo_event_analytic_account_id
                or not event.fudo_operation_analytic_account_id
            ):
                raise ValidationError(
                    'Los eventos activos deben tener cuenta analítica del evento '
                    'y tipo de operación analítico.'
                )
