from odoo import fields, models

SECUENCIA_SELECTION = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class EventEvent(models.Model):
    _inherit = 'event.event'

    image = fields.Image('Imagen', max_width=1920, max_height=1920)
    tipo_ids = fields.Many2many(
        'ponton.event.tipo',
        'ponton_event_tipo_event_rel',
        'event_id', 'tipo_id',
        string='Tipo de evento',
    )
    secuencia = fields.Selection(
        SECUENCIA_SELECTION, string='Secuencia', default='0',
    )
    supports_ids = fields.Many2many(
        'res.partner',
        'ponton_event_supports_partner_rel',
        'event_id', 'partner_id',
        string='Supports',
    )
