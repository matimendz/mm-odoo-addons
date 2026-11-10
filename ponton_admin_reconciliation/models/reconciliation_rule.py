from odoo import api, fields, models


class PontonReconciliationRule(models.Model):
    _name = 'ponton.reconciliation.rule'
    _description = 'Regla administrativa de conciliación'
    _order = 'priority, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=100, required=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        index=True,
    )
    journal_id = fields.Many2one('account.journal')
    reference_pattern = fields.Char(
        help='Texto a buscar en la referencia bancaria. No distingue mayúsculas/minúsculas.',
    )
    sign = fields.Selection(
        [
            ('any', 'Cualquiera'),
            ('inbound', 'Entrada'),
            ('outbound', 'Salida'),
        ],
        default='any',
        required=True,
    )
    min_amount = fields.Monetary(currency_field='currency_id')
    max_amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    issue_type = fields.Selection(
        selection=lambda self: self.env['ponton.reconciliation.issue']._fields['issue_type'].selection,
        required=True,
        default='other',
    )
    confidence = fields.Selection(
        selection=lambda self: self.env['ponton.reconciliation.issue']._fields['confidence'].selection,
        required=True,
        default='low',
    )
    probable_origin = fields.Selection(
        selection=lambda self: self.env['ponton.reconciliation.issue']._fields['probable_origin'].selection,
        required=True,
        default='unknown',
    )
    recommended_action = fields.Text(required=True)
    default_approved_action = fields.Selection(
        selection=lambda self: self.env['ponton.reconciliation.issue']._fields['approved_action'].selection,
        default='none',
        required=True,
    )
    requires_approval = fields.Boolean(default=True)
    target_account_id = fields.Many2one('account.account')

    def matches_statement_line(self, line):
        self.ensure_one()
        if self.company_id and line.company_id and self.company_id != line.company_id:
            return False
        if self.journal_id and self.journal_id != line.journal_id:
            return False
        if self.sign == 'inbound' and line.amount <= 0:
            return False
        if self.sign == 'outbound' and line.amount >= 0:
            return False
        abs_amount = abs(line.amount)
        if self.min_amount and abs_amount < self.min_amount:
            return False
        if self.max_amount and abs_amount > self.max_amount:
            return False
        if self.reference_pattern:
            ref = (line.payment_ref or '').lower()
            if self.reference_pattern.lower() not in ref:
                return False
        return True

    @api.model
    def _ensure_identification_account(self, company=None):
        company = company or self.env.company
        Account = self.env['account.account'].sudo()
        code = '1.1.1.02.008'
        domain = [('code', '=', code)]
        account = Account.search(domain, limit=1)
        vals = {
            'name': 'Liquidaciones por identificar',
            'account_type': 'asset_current',
            'reconcile': True,
        }
        if 'company_ids' in Account._fields:
            vals['company_ids'] = [(4, company.id)]
        elif 'company_id' in Account._fields:
            domain.append(('company_id', '=', company.id))
            vals['company_id'] = company.id
        if account:
            account.write(vals)
            return account
        vals['code'] = code
        return Account.create(vals)

