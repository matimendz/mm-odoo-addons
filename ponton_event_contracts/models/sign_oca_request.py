from odoo import models


class SignOcaRequest(models.Model):
    _inherit = 'sign.oca.request'

    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals or 'current_hash' in vals:
            contracts = self.env['ponton.event.contract'].search([
                ('sign_oca_request_id', 'in', self.ids),
            ])
            contracts._sync_from_sign_request()
        return result
