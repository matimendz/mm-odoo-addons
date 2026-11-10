import base64

from odoo import fields, http
from odoo.http import request
from odoo.tools.misc import format_datetime


class PontonLinksController(http.Controller):
    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def home_page(self, **kwargs):
        backend_redirect = self._redirect_odoo_host_to_backend()
        if backend_redirect:
            return backend_redirect
        return request.render('ponton_event.home_page', self._brand_values())

    @http.route(['/links', '/links/'], type='http', auth='public', website=True, sitemap=True)
    def links_page(self, **kwargs):
        backend_redirect = self._redirect_odoo_host_to_backend()
        if backend_redirect:
            return backend_redirect

        now = fields.Datetime.now()
        events = request.env['event.event'].sudo().search([
            ('active', '=', True),
            ('ponton_ticket_url', '!=', False),
            ('stage_id.name', '!=', 'Cancelado'),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', now),
        ], order='date_begin asc, id asc')

        values = {
            'ticket_events': [self._event_to_ticket_link(event) for event in events],
            **self._brand_values(),
        }
        return request.render('ponton_event.links_page', values)

    @http.route('/links/event-image/<int:event_id>', type='http', auth='public', website=True, sitemap=False)
    def event_image(self, event_id, **kwargs):
        event = request.env['event.event'].sudo().browse(event_id).exists()
        if not event or not event.active or not event.ponton_ticket_url or not event.image:
            return request.not_found()

        image = base64.b64decode(event.image)
        return request.make_response(image, headers=[
            ('Content-Type', self._image_content_type(image)),
            ('Cache-Control', 'public, max-age=3600'),
        ])

    def _brand_values(self):
        attachment = request.env['ir.attachment'].sudo().search([
            ('name', 'ilike', 'logo'),
            ('name', 'ilike', 'pontón'),
        ], order='id desc', limit=1) or request.env['ir.attachment'].sudo().search([
            ('name', 'ilike', 'logo'),
            ('name', 'ilike', 'ponton'),
        ], order='id desc', limit=1)
        return {
            'ponton_wordmark_url': f'/web/image/{attachment.id}' if attachment else '/web/image/67768',
        }

    def _redirect_odoo_host_to_backend(self):
        host = request.httprequest.host.split(':', 1)[0]
        if host == 'odoo.elponton.com.ar' and request.env.user._is_public():
            return request.redirect('/web', code=302)
        return False

    def _image_content_type(self, image):
        if image.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if image.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if image.startswith(b'RIFF') and image[8:12] == b'WEBP':
            return 'image/webp'
        if image.startswith(b'GIF87a') or image.startswith(b'GIF89a'):
            return 'image/gif'
        return 'application/octet-stream'

    def _event_to_ticket_link(self, event):
        event_date = ''
        if event.date_begin:
            event_date = format_datetime(
                request.env,
                event.date_begin,
                tz=request.context.get('tz'),
                dt_format='EEE d MMM, HH:mm',
            )

        return {
            'name': event.name,
            'ticket_url': event.ponton_ticket_url,
            'date': event_date,
            'venue': event.address_id.display_name if event.address_id else '',
            'types': ', '.join(event.tipo_ids.mapped('name')),
            'image_url': f'/links/event-image/{event.id}' if event.image else '',
        }
