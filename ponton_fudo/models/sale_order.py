from odoo import api, fields, models

FUDO_SALE_TYPE_SELECTION = [
    ('bar_abierto', 'Bar Abierto'),
    ('evento_propio', 'Evento Propio'),
    ('coproduccion', 'Coproducción'),
    ('evento_privado', 'Evento Privado'),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fudo_sale_type = fields.Selection(
        FUDO_SALE_TYPE_SELECTION,
        string='Tipo de noche (legacy)',
        default='bar_abierto',
        index=True,
        help='Campo legado para compatibilidad. La clasificación contable Fudo '
             'se toma de analytic_distribution.',
    )
    fudo_sale_id = fields.Char(
        string='ID Fudo',
        index=True,
        help='ID de la venta en Fudo POS. Permite trazabilidad hacia el sistema de origen.',
    )
    fudo_user_id = fields.Integer(
        string='ID usuario Fudo',
        index=True,
        help='ID del usuario/mozo de Fudo asociado a la venta.',
    )
    fudo_user_name = fields.Char(
        string='Usuario Fudo',
        index=True,
        help='Nombre del usuario/mozo de Fudo asociado a la venta.',
    )

    @api.model
    def ponton_fudo_reconcile_lines(self, line_ids):
        lines = self.env['account.move.line'].browse(line_ids).exists()
        if lines:
            lines.reconcile()
        return True
