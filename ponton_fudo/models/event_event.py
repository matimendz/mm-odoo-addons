from odoo import fields, models

FUDO_EVENT_TYPE_SELECTION = [
    ('evento_propio', 'Evento Propio'),
    ('coproduccion', 'Coproducción'),
    ('evento_privado', 'Evento Privado'),
]


class EventEvent(models.Model):
    _inherit = 'event.event'

    fudo_sale_type = fields.Selection(
        FUDO_EVENT_TYPE_SELECTION,
        string='Tipo Fudo',
        help='Clasifica las ventas Fudo importadas durante este evento. '
             'Vacío = las ventas del horario quedan como Bar Abierto.',
    )
