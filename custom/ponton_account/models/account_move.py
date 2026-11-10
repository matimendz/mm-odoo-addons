from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    fudo_user_name = fields.Char(
        string='Usuario Fudo',
        compute='_compute_fudo_user_name',
    )

    def _compute_fudo_user_name(self):
        origins = {m.invoice_origin for m in self if m.invoice_origin}
        if origins and 'sale.order' in self.env:
            sales = self.env['sale.order'].search([('fudo_sale_id', 'in', list(origins))])
            sale_map = {s.fudo_sale_id: s.fudo_user_name for s in sales}
        else:
            sale_map = {}
        for move in self:
            move.fudo_user_name = sale_map.get(move.invoice_origin) or False

    payment_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Diarios de pago',
        compute='_compute_payment_journal_ids',
    )

    def _compute_payment_journal_ids(self):
        invoice_types = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
        for move in self:
            if move.move_type not in invoice_types:
                move.payment_journal_ids = False
                continue
            pay_lines = move.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            )
            all_partial = pay_lines.matched_debit_ids | pay_lines.matched_credit_ids
            other_lines = (all_partial.debit_move_id | all_partial.credit_move_id).filtered(
                lambda l: l.move_id != move
            )
            payments = self.env['account.payment'].search(
                [('move_id', 'in', other_lines.mapped('move_id').ids)]
            )
            move.payment_journal_ids = payments.mapped('journal_id')
