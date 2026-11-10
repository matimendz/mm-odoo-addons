from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html_escape


class _ClauseFormatMap(dict):
    def __missing__(self, key):
        raise KeyError(key)


class PontonEventContractClause(models.Model):
    _name = 'ponton.event.contract.clause'
    _description = 'Clausula de contrato de evento'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [
            ('summary', 'Ficha'),
            ('split', 'Division de gastos e ingresos'),
            ('brands', 'Uso de marcas'),
            ('access', 'Ingresos, capacidad y reservas'),
            ('refreshments', 'Bebidas y refrigerios'),
            ('suppliers', 'Proveedores, armado y desarmado'),
            ('coexistence', 'Convivencia'),
            ('cancellation', 'Cancelacion'),
            ('signature', 'Firmas'),
            ('special', 'Especial'),
        ],
        required=True,
        default='special',
    )
    body = fields.Html(required=True, sanitize=True, translate=True)
    event_type_ids = fields.Many2many(
        'event.type',
        'ponton_contract_clause_event_type_rel',
        'clause_id',
        'event_type_id',
        string='Tipos de evento',
    )
    event_id = fields.Many2one('event.event', string='Evento especifico', ondelete='cascade')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _render_for_event(self, event):
        self.ensure_one()
        values = {
            'event_name': html_escape(event.ponton_contract_event_name or event.name or ''),
            'organizer_name': html_escape(event.organizer_id.display_name
                                          or event.ponton_organizer_text
                                          or ''),
            'guest_count': event.ponton_contract_guest_count or event.seats_max or 0,
            'final_capacity': event.ponton_contract_final_capacity or event.seats_max or 0,
            'manso_guest_passes': event.ponton_contract_manso_guest_passes or 0,
            'capacity_lock_days': event.ponton_contract_capacity_lock_days or 10,
            'supplier_deadline_hours': event.ponton_contract_supplier_deadline_hours or 48,
        }
        try:
            return Markup(self.body or '').format_map(_ClauseFormatMap(values))
        except (KeyError, ValueError) as error:
            raise ValidationError(_(
                'La clausula "%s" tiene placeholders invalidos. '
                'Usa llaves dobles para texto literal con { o }.'
            ) % self.display_name) from error
