from odoo import api, fields, models


PRIVATE_EVENT_TYPE_SELECTION = [
    ('wedding', 'Casamiento intimo'),
    ('birthday_30_40', 'Cumpleanos 30/40'),
    ('birthday_50_plus', 'Cumpleanos 50+'),
    ('corporate', 'Corporativo'),
    ('farewell', 'Despedida'),
    ('fifteen_high_profile', 'Fiesta de 15 perfil alto'),
    ('other', 'Otro'),
]

COMMERCIAL_MODEL_SELECTION = [
    ('package_per_person', 'Paquete cerrado por persona'),
    ('space_fee_plus_minimum_consumption', 'Alquiler + consumo minimo'),
]

GUEST_MODE_SELECTION = [
    ('seated', 'Sentados'),
    ('mixed', 'Mixto'),
    ('standing', 'Parados'),
    ('dance_floor', 'Con pista de baile'),
]

SEASON_BAND_SELECTION = [
    ('low', 'Baja'),
    ('medium', 'Media'),
    ('high', 'Alta'),
    ('very_high', 'Muy alta'),
]

CATERING_MODE_SELECTION = [
    ('ponton', 'Catering El Ponton'),
    ('external', 'Catering externo'),
    ('mixed', 'Mixto'),
]

BAR_MODE_SELECTION = [
    ('tickets', 'Consumo por ticket'),
    ('organizer_account', 'Cuenta del organizador'),
    ('guest_paid', 'Barra paga invitados'),
    ('mixed', 'Mixto'),
]

QUOTE_BLOCK_SELECTION = [
    ('base', 'A) Servicio base'),
    ('gastronomy', 'B) Gastronomia'),
    ('optional', 'C) Adicionales opcionales'),
    ('conditions', 'D) Condiciones'),
]


class PontonPrivateEventPackage(models.Model):
    _name = 'ponton.private.event.package'
    _description = 'Paquete de evento privado'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    commercial_model = fields.Selection(COMMERCIAL_MODEL_SELECTION, required=True)
    price_per_person = fields.Monetary(currency_field='currency_id')
    minimum_guests = fields.Integer(default=50)
    included_services = fields.Text()
    product_id = fields.Many2one('product.product', string='Producto de cotizacion')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)


class PontonPrivateEventRate(models.Model):
    _name = 'ponton.private.event.rate'
    _description = 'Tarifa de evento privado'
    _order = 'season_band, day_type, valid_from desc, id desc'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    season_band = fields.Selection(SEASON_BAND_SELECTION, required=True)
    day_type = fields.Selection(
        [('weekday_sunday', 'Lun-Jue / Domingo'), ('friday_saturday', 'Viernes / Sabado')],
        required=True,
    )
    space_fee = fields.Monetary(currency_field='currency_id')
    minimum_consumption = fields.Monetary(currency_field='currency_id')
    usd_reference = fields.Float('Referencia USD interna')
    valid_from = fields.Date()
    valid_to = fields.Date()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def matches_event(self, event):
        self.ensure_one()
        event_date = fields.Date.to_date(event.date_begin) if event.date_begin else fields.Date.context_today(event)
        if self.valid_from and event_date < self.valid_from:
            return False
        if self.valid_to and event_date > self.valid_to:
            return False
        return self.season_band == event.ponton_private_season_band


class PontonPrivateEventBlackout(models.Model):
    _name = 'ponton.private.event.blackout'
    _description = 'Fecha blackout de eventos privados'
    _order = 'date, name'

    name = fields.Char(required=True)
    date = fields.Date(required=True, index=True)
    reason = fields.Char()
    blocking = fields.Boolean(default=True)
    allow_manager_override = fields.Boolean(default=True)


class PontonPrivateEventPartnerService(models.Model):
    _name = 'ponton.private.event.partner.service'
    _description = 'Servicio tercerizado de evento privado'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ('decoration', 'Decoracion'),
            ('sound', 'Sonido profesional'),
            ('dj', 'DJ'),
            ('lighting', 'Iluminacion'),
            ('other', 'Otro'),
        ],
        required=True,
    )
    partner_id = fields.Many2one('res.partner')
    supplier_cost = fields.Monetary(currency_field='currency_id')
    markup_percent = fields.Float(default=10.0)
    sale_price = fields.Monetary(compute='_compute_sale_price', store=True, currency_field='currency_id')
    product_id = fields.Many2one('product.product', string='Producto de cotizacion')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('supplier_cost', 'markup_percent')
    def _compute_sale_price(self):
        for service in self:
            service.sale_price = service.supplier_cost * (1.0 + (service.markup_percent or 0.0) / 100.0)


class PontonPrivateEventChecklistTemplate(models.Model):
    _name = 'ponton.private.event.checklist.template'
    _description = 'Plantilla de checklist de evento privado'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    item_ids = fields.One2many('ponton.private.event.checklist.item', 'template_id')


class PontonPrivateEventChecklistItem(models.Model):
    _name = 'ponton.private.event.checklist.item'
    _description = 'Item de checklist de evento privado'
    _order = 'event_id, template_id, stage, sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    stage = fields.Selection(
        [
            ('pre_event_t7', 'Pre-evento T-7'),
            ('event_morning', 'Dia del evento - manana'),
            ('reception', 'Recibimiento'),
            ('during', 'Durante'),
            ('closing', 'Cierre'),
            ('post_event', 'Post-evento'),
        ],
        required=True,
    )
    template_id = fields.Many2one('ponton.private.event.checklist.template', ondelete='cascade')
    event_id = fields.Many2one('event.event', ondelete='cascade')
    responsible_id = fields.Many2one('res.users')
    is_critical = fields.Boolean(default=False)
    done = fields.Boolean(default=False)
    done_at = fields.Datetime(readonly=True)
    note = fields.Text()

    def write(self, vals):
        if vals.get('done') and 'done_at' not in vals:
            vals['done_at'] = fields.Datetime.now()
        elif vals.get('done') is False:
            vals['done_at'] = False
        return super().write(vals)


class PontonPrivateEventIncident(models.Model):
    _name = 'ponton.private.event.incident'
    _description = 'Incidente de evento privado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    event_id = fields.Many2one('event.event', required=True, ondelete='cascade', tracking=True)
    date = fields.Datetime(default=fields.Datetime.now, tracking=True)
    severity = fields.Selection(
        [('low', 'Baja'), ('medium', 'Media'), ('high', 'Alta')],
        default='medium',
        tracking=True,
    )
    description = fields.Text()
    resolution = fields.Text()
