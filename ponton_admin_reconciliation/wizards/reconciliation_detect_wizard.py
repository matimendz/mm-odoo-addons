from odoo import fields, models, _


class PontonReconciliationDetectWizard(models.TransientModel):
    _name = 'ponton.reconciliation.detect.wizard'
    _description = 'Detectar pendientes administrativos de conciliación'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    dry_run = fields.Boolean(default=False)
    include_reconciled = fields.Boolean(
        string='Incluir ya conciliados',
        default=False,
        help='Útil solo para auditorías. El uso normal detecta líneas abiertas.',
    )

    def action_detect(self):
        self.ensure_one()
        batch = self.env['ponton.reconciliation.batch'].create({
            'name': _('Detección %s a %s') % (self.date_from, self.date_to),
            'company_id': self.company_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'mode': 'dry_run' if self.dry_run else 'real',
        })
        created = existing = suggested = detected = errors = 0
        issue_model = self.env['ponton.reconciliation.issue'].sudo()

        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        if not self.include_reconciled:
            domain.append(('is_reconciled', '=', False))

        rules = self.env['ponton.reconciliation.rule'].sudo().search([
            ('active', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ])

        for line in self.env['account.bank.statement.line'].sudo().search(domain, order='date,id'):
            detected += 1
            vals = self._prepare_issue_values(line, batch, rules)
            if self.dry_run:
                if vals['state'] == 'suggested':
                    suggested += 1
                continue
            existing_issue = issue_model.search([
                ('company_id', '=', self.company_id.id),
                ('unique_key', '=', vals['unique_key']),
            ], limit=1)
            if existing_issue:
                existing += 1
                if not existing_issue.batch_id:
                    existing_issue.batch_id = batch.id
                continue
            try:
                issue = issue_model.create(vals)
                created += 1
                if issue.state == 'suggested':
                    suggested += 1
            except Exception as error:  # pragma: no cover - defensive audit log
                errors += 1
                batch.message_post(body=_(
                    'No se pudo crear issue para línea %(line)s: %(error)s'
                ) % {'line': line.display_name, 'error': error})

        batch.write({
            'finished_at': fields.Datetime.now(),
            'detected_count': detected,
            'created_count': created,
            'existing_count': existing,
            'suggested_count': suggested,
            'error_count': errors,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pendientes detectados'),
            'res_model': 'ponton.reconciliation.issue',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', batch.id)] if not self.dry_run else [('id', '=', False)],
            'context': {'default_batch_id': batch.id},
        }

    def _prepare_issue_values(self, line, batch, rules):
        rule = next((candidate for candidate in rules if candidate.matches_statement_line(line)), False)
        if rule:
            issue_type = rule.issue_type
            confidence = rule.confidence
            probable_origin = rule.probable_origin
            recommended_action = rule.recommended_action
            approved_action = rule.default_approved_action
            state = 'suggested' if confidence in ('medium', 'high') else 'new'
            rule_id = rule.id
        else:
            issue_type, confidence, probable_origin, recommended_action, approved_action, state = (
                self._fallback_classification(line)
            )
            rule_id = False

        return {
            'name': self._issue_name(line, issue_type),
            'company_id': self.company_id.id,
            'state': state,
            'issue_type': issue_type,
            'confidence': confidence,
            'date': line.date,
            'amount': line.amount,
            'currency_id': line.currency_id.id or self.company_id.currency_id.id,
            'journal_id': line.journal_id.id,
            'bank_statement_line_id': line.id,
            'partner_id': line.partner_id.id,
            'source_system': self._source_system(line),
            'external_reference': line.payment_ref,
            'probable_origin': probable_origin,
            'recommended_action': recommended_action,
            'approved_action': approved_action,
            'rule_id': rule_id,
            'batch_id': batch.id,
            'unique_key': 'bsl:%s:%s' % (line.id, issue_type),
        }

    def _fallback_classification(self, line):
        ref = line.payment_ref or ''
        journal = line.journal_id.name or ''
        if journal == 'Clover':
            return (
                'clover_unmatched_payment',
                'low',
                'clover',
                _('Validar contra cierre Clover/Fudo. No crear venta automática sin evidencia.'),
                'none',
                'review',
            )
        if journal == 'Banco Mercadopago':
            if 'MP Pago' in ref:
                return (
                    'mp_payment_without_expense',
                    'medium',
                    'supplier',
                    _('Buscar gasto Fudo/Odoo con método Mercadopago o cargar proveedor/comprobante faltante.'),
                    'manual_reconcile',
                    'suggested',
                )
            if 'Retiro' in ref:
                return (
                    'mp_withdrawal_to_macro',
                    'medium',
                    'mercadopago',
                    _('Agrupar por operación MP y buscar transferencia Macro neta dentro de 0 a 5 días hábiles.'),
                    'manual_reconcile',
                    'suggested',
                )
            return (
                'other',
                'low',
                'mercadopago',
                _('Clasificar movimiento MercadoPago por operación, impuesto, cobro, comisión o ajuste.'),
                'none',
                'review',
            )
        if journal == 'Banco Macro':
            if line.amount > 0 and 'TRANSF:' in ref:
                return (
                    'macro_transfer_origin',
                    'low',
                    'unidentified_liquidation',
                    _('Identificar origen: MP, Fiserv/Clover, Fudo Pagos, cliente o liquidación por identificar.'),
                    'classify_to_identification',
                    'review',
                )
            if 'CHEQUE' in ref:
                return (
                    'supplier_payment_missing',
                    'medium',
                    'supplier',
                    _('Vincular cheque con pago proveedor/factura o crear circuito de cheque emitido.'),
                    'manual_reconcile',
                    'suggested',
                )
            if 'AFIP' in ref:
                return (
                    'tax_payment_missing',
                    'medium',
                    'tax',
                    _('Registrar obligación fiscal y conciliar el débito Macro contra el asiento fiscal.'),
                    'create_tax_entry',
                    'suggested',
                )
            if 'TARJETA' in ref:
                return (
                    'credit_card_statement_missing',
                    'medium',
                    'credit_card',
                    _('Registrar resumen de tarjeta, imputar consumos y conciliar el débito Macro.'),
                    'create_credit_card_statement',
                    'suggested',
                )
        return (
            'other',
            'low',
            'unknown',
            _('Revisar manualmente y completar causa/acción administrativa.'),
            'none',
            'new',
        )

    def _source_system(self, line):
        journal = line.journal_id.name or ''
        if journal == 'Banco Macro':
            return 'bank_macro'
        if journal == 'Banco Mercadopago':
            return 'mercadopago'
        if journal == 'Clover':
            return 'clover'
        if journal == 'Fudo Pagos':
            return 'fudo_pagos'
        if journal == 'Efectivo':
            return 'cash'
        return 'other'

    def _issue_name(self, line, issue_type):
        issue_label = self.env['ponton.reconciliation.issue']._selection_label('issue_type', issue_type)
        return '%s - %s - %s' % (issue_label, line.date, line.amount)

