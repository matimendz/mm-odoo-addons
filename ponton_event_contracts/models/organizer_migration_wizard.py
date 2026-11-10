import re

from odoo import _, api, fields, models


class PontonEventOrganizerMigrationWizard(models.TransientModel):
    _name = 'ponton.event.organizer.migration.wizard'
    _description = 'Migracion asistida de organizadores de eventos'

    legacy_event_count = fields.Integer(
        string='Eventos con organizador legacy',
        compute='_compute_counts',
    )
    migratable_event_count = fields.Integer(
        string='Eventos a migrar',
        compute='_compute_counts',
    )
    overwrite_company_organizer = fields.Boolean(
        string='Reemplazar organizador por defecto',
        default=True,
        help='Migra eventos cuyo organizador actual es el contacto de la compania.',
    )

    @api.depends('overwrite_company_organizer')
    def _compute_counts(self):
        Event = self.env['event.event']
        legacy_domain = [('ponton_organizer_text', '!=', False)]
        legacy_count = Event.search_count(legacy_domain)
        for wizard in self:
            wizard.legacy_event_count = legacy_count
            wizard.migratable_event_count = len(wizard._get_migratable_events())

    def action_migrate(self):
        self.ensure_one()
        events = self._get_migratable_events()
        partners_created = self.env['res.partner']
        partners_reused = self.env['res.partner']
        migrated = self.env['event.event']
        for event in events:
            name = (event.ponton_organizer_text or '').strip()
            if not name:
                continue
            partner, created = self._find_or_create_partner(name)
            if created:
                partners_created |= partner
            else:
                partners_reused |= partner
            phone = self._clean_phone(event.ponton_contact_text)
            if phone and not partner.phone:
                partner.phone = phone
            event.organizer_id = partner
            migrated |= event

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Organizadores migrados'),
                'message': _(
                    '%(events)s eventos actualizados. %(created)s contactos creados, %(reused)s contactos reutilizados.'
                ) % {
                    'events': len(migrated),
                    'created': len(partners_created),
                    'reused': len(partners_reused),
                },
                'type': 'success',
                'sticky': False,
            },
        }

    def _get_migratable_events(self):
        self.ensure_one()
        events = self.env['event.event'].search([('ponton_organizer_text', '!=', False)])
        company_partner = self.env.company.partner_id
        if self.overwrite_company_organizer:
            return events.filtered(lambda event: not event.organizer_id or event.organizer_id == company_partner)
        return events.filtered(lambda event: not event.organizer_id)

    def _find_or_create_partner(self, name):
        partner = self.env['res.partner'].search([('name', '=ilike', name)], limit=1)
        if partner:
            return partner, False
        return self.env['res.partner'].create({'name': name}), True

    def _clean_phone(self, value):
        value = (value or '').strip()
        if not value:
            return False
        cleaned = re.sub(r'[^\d+]', '', value)
        if len(cleaned) < 6:
            return False
        return value
