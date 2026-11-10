from odoo import fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    ponton_contract_required = fields.Boolean('Requiere contrato')
    ponton_contract_kind = fields.Selection(
        [('coproduction', 'Coproduccion')],
        string='Tipo de contrato',
        default='coproduction',
    )
    ponton_contract_template_id = fields.Many2one(
        'sign.oca.template',
        string='Plantilla OCA Sign',
        domain="[('model', 'in', (False, 'event.event'))]",
    )
    ponton_contract_organizer_role_id = fields.Many2one(
        'sign.oca.role',
        string='Rol firmante organizador',
        default=lambda self: self.env.ref(
            'ponton_event_contracts.sign_role_event_organizer',
            raise_if_not_found=False,
        ),
    )
    ponton_contract_manso_role_id = fields.Many2one(
        'sign.oca.role',
        string='Rol firmante Manso',
        default=lambda self: self.env.ref(
            'ponton_event_contracts.sign_role_manso',
            raise_if_not_found=False,
        ),
    )
    ponton_contract_manso_partner_id = fields.Many2one(
        'res.partner',
        string='Firmante Manso por defecto',
        default=lambda self: self.env.company.partner_id,
    )
    ponton_contract_validity_days = fields.Integer('Validez para firma (dias)', default=10)
    ponton_contract_clause_ids = fields.Many2many(
        'ponton.event.contract.clause',
        'ponton_contract_clause_event_type_rel',
        'event_type_id',
        'clause_id',
        string='Clausulas',
    )
