# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    ponton_import_source = fields.Selection([
        ('macro', 'Banco Macro'),
        ('mercadopago', 'MercadoPago'),
    ], string='Origen El Pontón', readonly=True, copy=False)
    ponton_balance_expected = fields.Monetary(
        string='Saldo calculado El Pontón',
        readonly=True,
        copy=False,
    )
    ponton_balance_difference = fields.Monetary(
        string='Diferencia de saldo El Pontón',
        readonly=True,
        copy=False,
    )


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    ponton_mp_operation_type = fields.Char(
        string='Tipo operación MP',
        readonly=True,
        copy=False,
    )
    ponton_mp_movement_number = fields.Char(
        string='Movimiento MP',
        readonly=True,
        copy=False,
    )
    ponton_mp_related_operation = fields.Char(
        string='Operación relacionada MP',
        readonly=True,
        copy=False,
    )
