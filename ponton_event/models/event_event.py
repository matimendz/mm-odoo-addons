from odoo import api, fields, models
from odoo.exceptions import ValidationError

SECUENCIA_SELECTION = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]

ATTENDANCE_SOURCE_SELECTION = [
    ('manual', 'Manual'),
    ('quiero_entrar', 'Quiero Entrar'),
]


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _default_ponton_address_id(self):
        return self.env['res.partner'].search([('name', '=', 'El Pontón')], limit=1)

    image = fields.Image('Imagen', max_width=1920, max_height=1920)
    tipo_ids = fields.Many2many(
        'ponton.event.tipo',
        'ponton_event_tipo_event_rel',
        'event_id', 'tipo_id',
        string='Categorias de cartelera',
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
    ponton_planning_source = fields.Selection(
        [('excel', 'Excel')],
        string='Fuente de planificación',
        readonly=True,
    )
    ponton_planning_key = fields.Char('Clave planificación', readonly=True, index=True)
    ponton_planning_synced_at = fields.Datetime('Planificación sincronizada', readonly=True)
    ponton_organizer_text = fields.Char('Organizador planificación')
    ponton_contact_text = fields.Char('Contacto planificación')
    ponton_ticket_url = fields.Char('Link de entradas')
    ponton_attendance_source = fields.Selection(
        ATTENDANCE_SOURCE_SELECTION,
        string='Fuente de asistentes',
        default='manual',
        required=True,
        help='Solo los eventos propios pueden importar asistentes desde Quiero Entrar. '
             'El resto usa carga manual de asistentes efectivos.',
    )
    ponton_quiero_entrar_event_ref = fields.Char('Referencia evento Quiero Entrar')
    ponton_actual_attendee_count = fields.Integer('Asistentes efectivos')
    ponton_tableware = fields.Char('Vajilla evento')
    ponton_event_format = fields.Text('Formato evento')
    ponton_dj_technical = fields.Text('DJ y técnica')
    ponton_announced_social = fields.Selection(
        [('yes', 'Sí'), ('no', 'No'), ('unknown', 'Sin dato')],
        string='Anunciado en redes',
        default='unknown',
    )
    ponton_reservation_deadline_note = fields.Char('Límite de reservas')
    ponton_reservation_deadline_datetime = fields.Datetime('Fecha límite de reservas')
    ponton_open_datetime = fields.Datetime('Apertura')
    ponton_close_datetime = fields.Datetime('Cierre')
    ponton_staff_in_datetime = fields.Datetime('Ingreso personal')
    ponton_staff_out_datetime = fields.Datetime('Cierre personal')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if 'address_id' in fields_list and not vals.get('address_id'):
            address = self._default_ponton_address_id()
            if address:
                vals['address_id'] = address.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        address = self._default_ponton_address_id()
        if address:
            for vals in vals_list:
                vals.setdefault('address_id', address.id)
        events = super().create(vals_list)
        events._check_ponton_finalization()
        return events

    def write(self, vals):
        result = super().write(vals)
        if 'stage_id' in vals or 'ponton_actual_attendee_count' in vals:
            self._check_ponton_finalization()
        return result

    def _check_ponton_finalization(self):
        for event in self:
            if event.stage_id.name == 'Finalizado' and not event.ponton_actual_attendee_count:
                raise ValidationError('Para finalizar un evento cargá primero los asistentes efectivos.')

    @api.constrains(
        'stage_id',
        'ponton_actual_attendee_count',
        'ponton_open_datetime',
        'ponton_close_datetime',
        'ponton_staff_in_datetime',
        'ponton_staff_out_datetime',
        'ponton_ticket_url',
        'ponton_attendance_source',
        'ponton_quiero_entrar_event_ref',
    )
    def _check_ponton_planning(self):
        for event in self:
            if event.ponton_actual_attendee_count < 0:
                raise ValidationError('Los asistentes efectivos no pueden ser negativos.')
            if (
                event.ponton_open_datetime
                and event.ponton_close_datetime
                and event.ponton_open_datetime >= event.ponton_close_datetime
            ):
                raise ValidationError('La apertura debe ser anterior al cierre.')
            if (
                event.ponton_staff_in_datetime
                and event.ponton_staff_out_datetime
                and event.ponton_staff_in_datetime >= event.ponton_staff_out_datetime
            ):
                raise ValidationError('El ingreso del personal debe ser anterior al cierre del personal.')
            if event.ponton_ticket_url and not event.ponton_ticket_url.startswith(('http://', 'https://')):
                raise ValidationError('El link de entradas debe comenzar con http:// o https://.')
            if event.ponton_attendance_source == 'quiero_entrar' and not event._is_ponton_own_event():
                raise ValidationError(
                    'Solo los eventos con tipo de operación analítico "Evento Propio" '
                    'pueden importar asistentes desde Quiero Entrar.'
                )
            if event.ponton_quiero_entrar_event_ref and event.ponton_attendance_source != 'quiero_entrar':
                raise ValidationError(
                    'La referencia de Quiero Entrar solo se usa cuando la fuente de asistentes '
                    'es Quiero Entrar.'
                )

    def _is_ponton_own_event(self):
        self.ensure_one()
        operation = getattr(self, 'fudo_operation_analytic_account_id', False)
        return bool(operation and operation.name == 'Evento Propio')
