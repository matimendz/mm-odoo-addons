# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


def post_init_hook(cr_or_env, registry=None):
    env = cr_or_env if registry is None else api.Environment(cr_or_env, SUPERUSER_ID, {})
    company = env.company

    liquidity_type = env['account.account.type'].search([('type', '=', 'liquidity')], limit=1)
    expense_type = env['account.account.type'].search([('type', '=', 'expense')], limit=1)

    macro_journal = env['account.journal'].search([('type', '=', 'bank'), ('name', 'ilike', 'Banco Macro')], limit=1)
    mp_account = env['account.account'].search([('code', '=', '1.1.1.02.005'), ('company_id', '=', company.id)], limit=1)
    macro_account = env['account.account'].search([('code', '=', '1.1.1.02.004'), ('company_id', '=', company.id)], limit=1)
    fiserv_account = _get_or_create_account(
        env,
        code='1.1.1.02.006',
        name='Fiserv / Clover a liquidar',
        account_type=liquidity_type,
        company=company,
    )

    mp_journal = _get_or_create_journal(env, 'Banco Mercadopago', 'MPAGO', mp_account, company)
    _get_or_create_journal(env, 'Fiserv / Clover', 'FISER', fiserv_account, company)

    fee_account = env['account.account'].search([('code', '=', '5.2.1.01.070'), ('company_id', '=', company.id)], limit=1)
    bank_tax_account = env['account.account'].search([('code', '=', '5.4.3.01.010'), ('company_id', '=', company.id)], limit=1)

    if not fee_account:
        fee_account = _get_or_create_account(env, '5.2.1.01.070', 'Comisiones Pagadas', expense_type, company)
    if not bank_tax_account:
        bank_tax_account = _get_or_create_account(env, '5.4.3.01.010', 'Impuestos a los débitos y créditos bancarios', expense_type, company)

    if macro_journal:
        _get_or_create_reconcile_model(env, 'El Pontón - Liquidación Fiserv/Clover', 'LIQ COMER FISERV', 'amount_received', fiserv_account, macro_journal, company)
        _get_or_create_reconcile_model(env, 'El Pontón - Impuesto DBCR débito', 'DBCR 25413 S/DB TASA GRAL', 'amount_paid', bank_tax_account, macro_journal, company)
        _get_or_create_reconcile_model(env, 'El Pontón - Impuesto DBCR crédito', 'DBCR 25413 S/CR TASA GRAL', 'amount_paid', bank_tax_account, macro_journal, company)
        _get_or_create_reconcile_model(env, 'El Pontón - Comisiones bancarias', 'COMISION', 'amount_paid', fee_account, macro_journal, company)
        _get_or_create_reconcile_model(env, 'El Pontón - IVA/percepción bancaria', 'DEBITO FISCAL IVA', 'amount_paid', bank_tax_account, macro_journal, company)
    if mp_journal:
        _get_or_create_reconcile_model(env, 'El Pontón MP - Costo MercadoPago', 'Costo de Mercado Pago', 'amount_paid', fee_account, mp_journal, company)
        _get_or_create_reconcile_model(env, 'El Pontón MP - Impuesto cobros/pagos', 'Impuesto sobre los Créditos y Débitos', 'amount_paid', bank_tax_account, mp_journal, company)
        _get_or_create_reconcile_model(env, 'El Pontón MP - Retención SIRCUPA', 'Retención Impuesto Ingresos Brutos', 'amount_paid', bank_tax_account, mp_journal, company)
        if macro_account:
            _get_or_create_reconcile_model(env, 'El Pontón MP - Retiro a Banco Macro', 'Retiro de dinero', 'amount_paid', macro_account, mp_journal, company)


def _get_or_create_account(env, code, name, account_type, company):
    account = env['account.account'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
    if account:
        return account
    return env['account.account'].create({
        'code': code,
        'name': name,
        'user_type_id': account_type.id,
        'company_id': company.id,
        'reconcile': True,
    })


def _get_or_create_journal(env, name, code, account, company):
    journal = env['account.journal'].search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
    if not journal and account:
        journal = env['account.journal'].search([
            ('type', '=', 'bank'),
            ('default_account_id', '=', account.id),
            ('company_id', '=', company.id),
        ], limit=1)
    if not journal:
        journal = env['account.journal'].search([
            ('type', '=', 'bank'),
            ('name', '=', name),
            ('company_id', '=', company.id),
        ], limit=1)
    if journal:
        if account and journal.default_account_id != account:
            journal.default_account_id = account.id
        return journal
    return env['account.journal'].create({
        'name': name,
        'code': code,
        'type': 'bank',
        'company_id': company.id,
        'default_account_id': account.id,
    })


def _get_or_create_reconcile_model(env, name, label, nature, account, journal, company):
    model = env['account.reconcile.model'].search([('name', '=', name), ('company_id', '=', company.id)], limit=1)
    vals = {
        'name': name,
        'sequence': 20,
        'rule_type': 'writeoff_suggestion',
        'auto_reconcile': False,
        'match_nature': nature,
        'match_label': 'contains',
        'match_label_param': label,
        'match_text_location_label': True,
        'match_text_location_note': True,
        'match_text_location_reference': True,
        'match_journal_ids': [(6, 0, journal.ids)],
        'line_ids': [(0, 0, {
            'account_id': account.id,
            'amount_type': 'percentage',
            'amount_string': '100',
            'label': name,
        })],
    }
    if model:
        model.write({key: value for key, value in vals.items() if key != 'line_ids'})
        if not model.line_ids:
            model.write({'line_ids': vals['line_ids']})
        return model
    return env['account.reconcile.model'].create(vals)
