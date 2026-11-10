import logging
_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Elimina las vistas y campos creados por Odoo Studio en event.event."""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    studio_views = env['ir.ui.view'].search([
        ('model', '=', 'event.event'),
        ('name', 'like', 'Odoo Studio:%'),
    ])
    if studio_views:
        _logger.info("Eliminando %d vistas de Studio en event.event", len(studio_views))
        studio_views.unlink()

    studio_fields = env['ir.model.fields'].search([
        ('model', '=', 'event.event'),
        ('name', 'in', ['x_studio_selection_field_1mg0R', 'x_studio_supports']),
    ])
    if studio_fields:
        _logger.info("Eliminando %d campos de Studio en event.event", len(studio_fields))
        studio_fields.unlink()
