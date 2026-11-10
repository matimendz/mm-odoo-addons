from odoo import fields, models


class FudoExpenseAnalyticRule(models.Model):
    _name = 'ponton.fudo.expense.analytic.rule'
    _description = 'Regla analítica para gastos Fudo'
    _order = 'priority, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=100, required=True)
    keyword = fields.Char(
        help='Texto a buscar en comentario, número de comprobante o proveedor. '
             'No distingue mayúsculas/minúsculas.',
    )
    provider_keyword = fields.Char(
        string='Proveedor contiene',
        help='Texto a buscar en el proveedor Fudo/Odoo.',
    )
    fudo_category_id = fields.Char(string='ID categoría Fudo', index=True)
    fudo_category_name = fields.Char(string='Categoría Fudo')
    operation_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tipo de operación',
        required=True,
        domain="[('plan_id.name', '=', 'Tipo de Operación')]",
    )
    use_event_date = fields.Boolean(
        string='Asignar evento por fecha',
        default=True,
        help='Si está activo, el integrador buscará un evento entre el inicio y fin + 12h.',
    )
