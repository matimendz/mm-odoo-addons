from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    ponton_contract_required_for_events = fields.Boolean(
        string='Requiere contrato en eventos',
        help='Los eventos con este tipo de operacion requieren contrato online.',
    )
