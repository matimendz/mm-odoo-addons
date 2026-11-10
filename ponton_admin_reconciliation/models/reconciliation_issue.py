from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PontonReconciliationIssue(models.Model):
    _name = 'ponton.reconciliation.issue'
    _description = 'Pendiente administrativo de conciliación'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        [
            ('new', 'Nuevo'),
            ('review', 'En revisión'),
            ('suggested', 'Sugerido'),
            ('approved', 'Aprobado'),
            ('applied', 'Aplicado'),
            ('blocked', 'Bloqueado'),
            ('discarded', 'Descartado'),
        ],
        default='new',
        required=True,
        tracking=True,
        index=True,
    )
    issue_type = fields.Selection(
        [
            ('macro_transfer_origin', 'Macro: transferencia sin origen'),
            ('mp_payment_without_expense', 'MP: pago sin gasto'),
            ('mp_withdrawal_to_macro', 'MP: retiro a Macro'),
            ('clover_unmatched_payment', 'Clover: cobro no identificado'),
            ('payment_method_reclassification', 'Reclasificación de medio de pago'),
            ('supplier_payment_missing', 'Pago proveedor faltante'),
            ('tax_payment_missing', 'Pago fiscal faltante'),
            ('credit_card_statement_missing', 'Resumen tarjeta faltante'),
            ('cash_difference', 'Diferencia de caja'),
            ('other', 'Otro'),
        ],
        required=True,
        default='other',
        tracking=True,
        index=True,
    )
    confidence = fields.Selection(
        [
            ('low', 'Baja'),
            ('medium', 'Media'),
            ('high', 'Alta'),
        ],
        default='low',
        required=True,
        tracking=True,
    )
    date = fields.Date(required=True, index=True, tracking=True)
    amount = fields.Monetary(required=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    journal_id = fields.Many2one('account.journal', index=True)
    bank_statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Línea de extracto',
        index=True,
        ondelete='cascade',
    )
    payment_id = fields.Many2one('account.payment', string='Pago')
    move_id = fields.Many2one('account.move', string='Asiento/factura')
    move_line_id = fields.Many2one('account.move.line', string='Apunte')
    partner_id = fields.Many2one('res.partner', string='Contacto')
    source_system = fields.Selection(
        [
            ('bank_macro', 'Banco Macro'),
            ('mercadopago', 'MercadoPago'),
            ('clover', 'Clover/Fiserv'),
            ('fudo_pagos', 'Fudo Pagos'),
            ('fudo', 'Fudo'),
            ('cash', 'Caja'),
            ('manual', 'Manual'),
            ('other', 'Otro'),
        ],
        default='other',
        index=True,
    )
    external_reference = fields.Char(index=True)
    probable_origin = fields.Selection(
        [
            ('mercadopago', 'MercadoPago'),
            ('clover', 'Clover/Fiserv'),
            ('fudo_pagos', 'Fudo Pagos'),
            ('supplier', 'Proveedor'),
            ('tax', 'Impuesto'),
            ('credit_card', 'Tarjeta de crédito'),
            ('customer', 'Cliente/tercero'),
            ('cash', 'Caja'),
            ('unidentified_liquidation', 'Liquidación por identificar'),
            ('unknown', 'Desconocido'),
        ],
        default='unknown',
        tracking=True,
    )
    recommended_action = fields.Text()
    approved_action = fields.Selection(
        [
            ('none', 'Sin acción contable'),
            ('classify_to_identification', 'Clasificar a Liquidaciones por identificar'),
            ('manual_reconcile', 'Conciliación manual asistida'),
            ('reclassify_payment_method', 'Reclasificar medio de pago'),
            ('create_supplier_payment', 'Crear/vincular pago proveedor'),
            ('create_tax_entry', 'Crear asiento fiscal'),
            ('create_credit_card_statement', 'Crear resumen de tarjeta'),
            ('discard', 'Descartar'),
        ],
        default='none',
        tracking=True,
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        tracking=True,
    )
    rule_id = fields.Many2one('ponton.reconciliation.rule', string='Regla')
    batch_id = fields.Many2one('ponton.reconciliation.batch', string='Corrida')
    notes = fields.Text()
    applied_at = fields.Datetime(readonly=True)
    applied_by_id = fields.Many2one('res.users', readonly=True)
    unique_key = fields.Char(required=True, index=True, copy=False)

    _unique_issue_key = models.Constraint(
        'unique(company_id, unique_key)',
        'Ya existe un pendiente para esta clave de conciliación.',
    )

    @api.constrains('state', 'approved_action')
    def _check_approved_action(self):
        for issue in self:
            if issue.state == 'approved' and issue.approved_action == 'none':
                raise ValidationError(_('Un pendiente aprobado debe tener una acción aprobada.'))

    @api.model
    def _selection_label(self, field_name, value):
        return dict(self._fields[field_name].selection).get(value, value)

    def action_mark_review(self):
        self.write({'state': 'review'})

    def action_mark_suggested(self):
        self.write({'state': 'suggested'})

    def action_approve(self):
        for issue in self:
            if issue.approved_action == 'none':
                issue.approved_action = 'manual_reconcile'
        self.write({'state': 'approved'})

    def action_block(self):
        self.write({'state': 'blocked'})

    def action_discard(self):
        self.write({'state': 'discarded', 'approved_action': 'discard'})

    def action_reset(self):
        self.write({'state': 'new', 'approved_action': 'none'})

    def action_apply(self):
        for issue in self:
            issue._apply_approved_action()

    def _apply_approved_action(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Solo se pueden aplicar pendientes aprobados.'))
        if self.approved_action == 'discard':
            self.write({
                'state': 'discarded',
                'applied_at': fields.Datetime.now(),
                'applied_by_id': self.env.user.id,
            })
            return
        if self.approved_action == 'classify_to_identification':
            self._apply_classify_statement_line_to_identification()
            return
        raise UserError(_(
            'La acción "%s" requiere ejecución manual o un automatismo específico.'
        ) % self._selection_label('approved_action', self.approved_action))

    def _apply_classify_statement_line_to_identification(self):
        self.ensure_one()
        if not self.bank_statement_line_id:
            raise UserError(_('El pendiente no tiene línea de extracto vinculada.'))
        if self.bank_statement_line_id.is_reconciled:
            self.write({
                'state': 'applied',
                'applied_at': fields.Datetime.now(),
                'applied_by_id': self.env.user.id,
            })
            return
        account = self.env['ponton.reconciliation.rule']._ensure_identification_account(self.company_id)
        self.bank_statement_line_id.ponton_reconcile_to_account(
            account,
            self.name,
        )
        self.write({
            'state': 'applied',
            'applied_at': fields.Datetime.now(),
            'applied_by_id': self.env.user.id,
        })


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    ponton_reconciliation_issue_ids = fields.One2many(
        'ponton.reconciliation.issue',
        'bank_statement_line_id',
        string='Pendientes administrativos',
    )

    def ponton_reconcile_to_account(self, account, label):
        """Classify a bank line to an account using the OCA bank reconciliation API."""
        self.ensure_one()
        reconcile_data = self.reconcile_data_info or {}
        data = reconcile_data.get('data') or []
        suspense_line = next((item for item in data if item.get('kind') == 'suspense'), None)
        if not suspense_line:
            raise UserError(_('La línea no tiene línea transitoria para reemplazar.'))
        suspense_line.update({
            'account_id': [account.id, account.display_name],
            'name': label,
            'kind': 'other',
        })
        reconcile_data['data'] = data
        reconcile_data['manual_reference'] = suspense_line.get('reference')
        reconcile_data['can_reconcile'] = True
        self.write({'reconcile_data_info': reconcile_data})
        self.reconcile_bank_line()
