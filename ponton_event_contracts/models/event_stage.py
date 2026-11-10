from odoo import fields, models


class EventStage(models.Model):
    _inherit = 'event.stage'

    is_contract_confirmed_stage = fields.Boolean(
        string='Etapa confirmada con contrato',
        help='Los eventos de coproduccion que requieren contrato solo pueden entrar '
             'en esta etapa si tienen un contrato firmado y vigente.',
    )
