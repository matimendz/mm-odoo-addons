# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    ponton_macro_use_opening_balance = fields.Boolean(
        string='Usar saldo inicial Macro',
        help='Usa un saldo inicial fijo para los extractos Banco Macro importados desde este diario.',
    )
    ponton_macro_opening_balance_date = fields.Date(
        string='Fecha saldo inicial Macro',
        default='2026-01-01',
    )
    ponton_macro_opening_balance = fields.Float(
        string='Saldo inicial Macro',
        digits='Account',
    )
    ponton_macro_import_from_date = fields.Date(
        string='Importar Macro desde',
        default='2026-01-01',
        help='Ignora movimientos anteriores a esta fecha al importar extractos Banco Macro.',
    )
