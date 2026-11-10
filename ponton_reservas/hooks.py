import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _migrate_studio_tags(env)
    _migrate_studio_reservas(env)


def _model_exists(env, model_name):
    return bool(env['ir.model'].search([('model', '=', model_name)], limit=1))


def _migrate_studio_tags(env):
    if not _model_exists(env, 'x_reserva_tag'):
        return

    legacy_tags = env['x_reserva_tag'].with_context(active_test=False).search([])
    for legacy in legacy_tags:
        tag = env['ponton.reserva.tag'].search([('legacy_x_reserva_tag_id', '=', legacy.id)], limit=1)
        vals = {
            'name': legacy.x_name,
            'color': legacy.x_color,
            'legacy_x_reserva_tag_id': legacy.id,
        }
        if tag:
            tag.write(vals)
        else:
            env['ponton.reserva.tag'].create(vals)
    _logger.info("Migrated %d Studio reservation tags", len(legacy_tags))


def _migrate_studio_reservas(env):
    if not _model_exists(env, 'x_reserva'):
        return

    legacy_reservas = env['x_reserva'].with_context(active_test=False).search([])
    tag_map = {
        tag.legacy_x_reserva_tag_id: tag.id
        for tag in env['ponton.reserva.tag'].search([('legacy_x_reserva_tag_id', '!=', False)])
    }
    state_map = {
        'draft': 'draft',
        'confirmed': 'confirmed',
        'Cancelado': 'cancelled',
        'cancelled': 'cancelled',
    }

    for legacy in legacy_reservas:
        reserva = env['ponton.reserva'].with_context(active_test=False).search([
            ('legacy_x_reserva_id', '=', legacy.id),
        ], limit=1)
        tag_ids = [
            tag_map[tag.id]
            for tag in legacy.x_studio_tag_ids
            if tag.id in tag_map
        ]
        vals = {
            'active': legacy.x_active,
            'partner_id': legacy.x_studio_partner_id.id or False,
            'user_id': legacy.x_studio_user_id.id or False,
            'reservation_date': legacy.x_studio_date,
            'reservation_time': legacy.x_studio_horario,
            'guest_count': legacy.x_studio_cantidad,
            'state': state_map.get(legacy.x_studio_selection_field_0wVj5 or 'draft', 'draft'),
            'sector': legacy.x_studio_sector or False,
            'source': legacy.x_studio_medio or False,
            'notes': legacy.x_studio_notes,
            'partner_phone': legacy.x_studio_partner_phone or legacy.x_studio_telfono,
            'partner_email': legacy.x_studio_partner_email or legacy.x_studio_email,
            'legacy_x_reserva_id': legacy.id,
            'tag_ids': [(6, 0, tag_ids)],
        }
        if legacy.x_name:
            vals['name'] = legacy.x_name
        if reserva:
            reserva.write(vals)
        else:
            env['ponton.reserva'].create(vals)
    _logger.info("Migrated %d Studio reservations", len(legacy_reservas))
