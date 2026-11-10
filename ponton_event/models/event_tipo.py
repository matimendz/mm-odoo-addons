from odoo import fields, models


class PontonEventTipo(models.Model):
    _name = 'ponton.event.tipo'
    _description = 'Tipo de Evento'
    _order = 'name'

    name = fields.Char('Nombre', required=True, translate=True)
    color = fields.Integer('Color')
    event_ids = fields.Many2many('event.event', string='Eventos')
