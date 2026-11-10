from odoo import api, fields, models


class PontonReservaTag(models.Model):
    _name = 'ponton.reserva.tag'
    _description = 'Etiqueta de Reserva'
    _order = 'name'

    name = fields.Char('Nombre', required=True)
    color = fields.Integer('Color')
    legacy_x_reserva_tag_id = fields.Integer('ID Studio anterior', copy=False, index=True, readonly=True)


class PontonReserva(models.Model):
    _name = 'ponton.reserva'
    _description = 'Reserva'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reservation_date desc, reservation_time asc, id desc'

    name = fields.Char('Nombre', compute='_compute_name', store=True, readonly=False)
    active = fields.Boolean('Activo', default=True)
    partner_id = fields.Many2one('res.partner', string='Contacto', tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string='Quien toma reserva',
        default=lambda self: self.env.user,
        tracking=True,
    )
    reservation_date = fields.Date('Fecha', tracking=True)
    reservation_time = fields.Float('Horario', tracking=True, aggregator=None)
    guest_count = fields.Integer('Personas', tracking=True)
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        tracking=True,
    )
    sector = fields.Selection(
        [
            ('Rio', 'Rio'),
            ('Galeria', 'Galeria'),
            ('Terraza', 'Terraza'),
            ('Barra', 'Barra'),
            ('Patio', 'Patio'),
            ('Aldea', 'Aldea'),
            ('Muelle', 'Muelle'),
        ],
        string='Sector',
        tracking=True,
    )
    source = fields.Selection(
        [
            ('Whatsapp', 'Whatsapp'),
            ('Instagram', 'Instagram'),
            ('Pagina web', 'Página web'),
            ('Externo', 'Externo'),
            ('Presencial en bar', 'Presencial en bar'),
        ],
        string='Medio',
        tracking=True,
    )
    tag_ids = fields.Many2many('ponton.reserva.tag', string='Categorías')
    notes = fields.Html('Notas')
    partner_phone = fields.Char('Teléfono')
    partner_email = fields.Char('Correo electrónico')
    legacy_x_reserva_id = fields.Integer('ID Studio anterior', copy=False, index=True, readonly=True)

    @api.depends('partner_id', 'reservation_date')
    def _compute_name(self):
        for reserva in self:
            partner_name = reserva.partner_id.display_name or 'Reserva'
            if reserva.reservation_date:
                reserva.name = '%s - %s' % (partner_name, reserva.reservation_date)
            else:
                reserva.name = partner_name

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
