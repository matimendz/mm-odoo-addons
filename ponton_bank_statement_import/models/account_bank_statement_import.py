# -*- coding: utf-8 -*-

import hashlib
from datetime import datetime
from io import BytesIO
import base64

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from odoo import _, models
from odoo.exceptions import UserError


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def action_preview_macro_excel(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_('Seleccioná un archivo Banco Macro para previsualizar.'))
        if len(self.attachment_ids) > 1:
            raise UserError(_('La vista previa Macro acepta un solo archivo por vez.'))

        currency_code, account_number, statements = self._parse_file(self.attachment_ids.datas and base64.b64decode(self.attachment_ids.datas))
        if not statements or statements[0].get('ponton_import_source') not in (False, 'macro'):
            raise UserError(_('No se detectaron movimientos Banco Macro en el archivo.'))

        statement = statements[0]
        transactions = statement['transactions']
        total = sum(line['amount'] for line in transactions)
        balance_start = statement.get('balance_start')
        balance_end_real = statement.get('balance_end_real')
        balance_expected = balance_start + total if balance_start is not None else None
        difference = balance_expected - balance_end_real if balance_expected is not None and balance_end_real is not None else None

        message = [
            _('Vista previa Banco Macro'),
            '',
            _('Moneda: %s') % (currency_code or '-'),
            _('Cuenta: %s') % (account_number or '-'),
            _('Movimientos: %s') % len(transactions),
            _('Desde: %s') % transactions[0]['date'].strftime('%Y-%m-%d'),
            _('Hasta: %s') % transactions[-1]['date'].strftime('%Y-%m-%d'),
            _('Total movimientos: %.2f') % total,
        ]
        if balance_start is not None:
            message.append(_('Saldo inicial: %.2f') % balance_start)
        if balance_end_real is not None:
            message.append(_('Saldo final banco: %.2f') % balance_end_real)
        if difference is not None:
            message.append(_('Diferencia calculada: %.2f') % difference)
        raise UserError('\n'.join(message))

    def action_preview_mercadopago_excel(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_('Seleccioná un archivo MercadoPago para previsualizar.'))
        if len(self.attachment_ids) > 1:
            raise UserError(_('La vista previa MercadoPago acepta un solo archivo por vez.'))

        currency_code, account_number, statements = self._parse_file(base64.b64decode(self.attachment_ids.datas))
        if not statements or statements[0].get('ponton_import_source') != 'mercadopago':
            raise UserError(_('No se detectó un archivo de movimientos de MercadoPago.'))

        statement = statements[0]
        transactions = statement['transactions']
        totals_by_type = {}
        for line in transactions:
            operation_type = line.get('ponton_mp_operation_type') or _('Sin tipo')
            totals_by_type.setdefault(operation_type, [0, 0.0])
            totals_by_type[operation_type][0] += 1
            totals_by_type[operation_type][1] += line['amount']

        message = [
            _('Vista previa MercadoPago'),
            '',
            _('Moneda: %s') % (currency_code or '-'),
            _('Movimientos: %s') % len(transactions),
            _('Desde: %s') % transactions[0]['date'].strftime('%Y-%m-%d'),
            _('Hasta: %s') % transactions[-1]['date'].strftime('%Y-%m-%d'),
            _('Total neto movimientos: %.2f') % sum(line['amount'] for line in transactions),
            '',
            _('Por tipo:'),
        ]
        for operation_type, values in sorted(totals_by_type.items()):
            message.append('- %s: %s movimientos / %.2f' % (operation_type, values[0], values[1]))
        raise UserError('\n'.join(message))

    def _parse_file(self, data_file):
        if self._is_xls_file(data_file):
            return self._parse_macro_xls(data_file)
        if self._is_xlsx_file(data_file):
            return self._parse_xlsx(data_file)
        return super()._parse_file(data_file)

    @staticmethod
    def _is_xls_file(data_file):
        return data_file[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'

    @staticmethod
    def _is_xlsx_file(data_file):
        return data_file[:2] == b'PK'

    def _parse_macro_xls(self, data_file):
        try:
            import xlrd
        except ImportError:
            raise UserError(_('Falta la librería Python xlrd para leer archivos .xls de Banco Macro.'))

        try:
            book = xlrd.open_workbook(file_contents=data_file)
        except Exception:
            return super()._parse_file(data_file)

        sheet = book.sheet_by_index(0)
        rows = []
        for row_idx in range(sheet.nrows):
            rows.append([self._xlrd_cell_value(book, sheet, row_idx, col_idx) for col_idx in range(sheet.ncols)])
        return self._parse_macro_rows(rows)

    def _parse_xlsx(self, data_file):
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise UserError(_('Falta la librería Python openpyxl para leer archivos .xlsx.'))

        try:
            workbook = load_workbook(BytesIO(data_file), read_only=True, data_only=True)
        except Exception:
            return super()._parse_file(data_file)

        sheet = workbook.worksheets[0]
        rows = [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]
        if self._find_macro_header(rows) is not None:
            return self._parse_macro_rows(rows)
        if self._find_mp_header(rows) is not None:
            return self._parse_mp_rows(rows)
        return super()._parse_file(data_file)

    @staticmethod
    def _xlrd_cell_value(book, sheet, row_idx, col_idx):
        import xlrd

        cell = sheet.cell(row_idx, col_idx)
        if cell.ctype == xlrd.XL_CELL_DATE:
            return xlrd.xldate_as_datetime(cell.value, book.datemode)
        return cell.value

    def _parse_macro_rows(self, rows):
        header_idx = self._find_macro_header(rows)
        if header_idx is None:
            return super()._parse_file(b'')

        header = rows[header_idx]
        colmap = self._macro_colmap(header)
        account_number = self._find_macro_account_number(rows[:header_idx]) or None
        journal = self._get_import_journal()
        transactions = []

        for source_idx, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            if not self._row_has_value(row, colmap.get('concept')):
                continue

            date = self._to_date(row[colmap['date']])
            concept = self._to_text(row[colmap['concept']])
            amount = self._to_float(row[colmap['amount']])
            if not date or not concept or amount is None:
                continue
            if journal and journal.ponton_macro_import_from_date and date < journal.ponton_macro_import_from_date:
                continue

            reference = self._to_text(row[colmap['reference']])
            causal = self._to_text(row[colmap['causal']])
            balance = self._to_float(row[colmap['balance']]) if colmap.get('balance') is not None else None

            transactions.append({
                'source_idx': source_idx,
                'date': date,
                'name': concept,
                'payment_ref': concept,
                'amount': amount,
                'ref': reference,
                'internal_notes': self._build_note(reference, causal, concept, balance),
                'transaction_type': causal,
                'unique_import_id': self._unique_import_id(account_number, date, reference, causal, concept, amount),
                'balance': balance,
            })

        if not transactions:
            raise UserError(_('No se encontraron movimientos válidos en el extracto de Banco Macro.'))

        transactions.sort(key=lambda vals: (vals['date'], -vals['source_idx']))
        first_balance = transactions[0].get('balance')
        last_balance = transactions[-1].get('balance')

        statement_vals = {
            'name': _('Banco Macro %s') % transactions[-1]['date'].strftime('%Y-%m-%d'),
            'date': transactions[-1]['date'],
            'transactions': [
                {key: value for key, value in transaction.items() if key not in ('source_idx', 'balance')}
                for transaction in transactions
            ],
        }
        if journal and journal.ponton_macro_use_opening_balance:
            statement_vals['balance_start'] = journal.ponton_macro_opening_balance
            opening_date = journal.ponton_macro_opening_balance_date
            if opening_date:
                statement_vals['name'] = _('Banco Macro desde %s hasta %s') % (
                    opening_date.strftime('%Y-%m-%d'),
                    transactions[-1]['date'].strftime('%Y-%m-%d'),
                )
        elif first_balance is not None:
            statement_vals['balance_start'] = first_balance - transactions[0]['amount']
        if last_balance is not None:
            statement_vals['balance_end_real'] = last_balance
        if statement_vals.get('balance_start') is not None and statement_vals.get('balance_end_real') is not None:
            expected_balance = statement_vals['balance_start'] + sum(line['amount'] for line in statement_vals['transactions'])
            statement_vals['ponton_import_source'] = 'macro'
            statement_vals['ponton_balance_expected'] = expected_balance
            statement_vals['ponton_balance_difference'] = expected_balance - statement_vals['balance_end_real']

        return 'ARS', account_number, [statement_vals]

    def _parse_mp_rows(self, rows):
        header_idx = self._find_mp_header(rows)
        if header_idx is None:
            return super()._parse_file(b'')

        header = rows[header_idx]
        colmap = self._mp_colmap(header)
        transactions = []

        for source_idx, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            payment_date = self._to_mp_datetime(row[colmap['payment_date']])
            operation_type = self._to_text(row[colmap['operation_type']])
            movement_number = self._to_text(row[colmap['movement_number']])
            related_operation = self._to_text(row[colmap['related_operation']])
            amount = self._to_float(row[colmap['amount']])
            if not payment_date or not operation_type or amount is None:
                continue

            date = self._mp_local_date(payment_date)
            transaction = {
                'source_idx': source_idx,
                'date': date,
                'name': self._mp_line_name(operation_type, related_operation, movement_number),
                'payment_ref': self._mp_line_name(operation_type, related_operation, movement_number),
                'amount': amount,
                'ref': movement_number,
                'internal_notes': self._mp_note(payment_date, operation_type, movement_number, related_operation),
                'transaction_type': operation_type,
                'unique_import_id': self._mp_unique_import_id(movement_number, related_operation, operation_type, amount),
                'ponton_mp_operation_type': operation_type,
                'ponton_mp_movement_number': movement_number,
                'ponton_mp_related_operation': related_operation,
            }
            transactions.append(transaction)

        if not transactions:
            raise UserError(_('No se encontraron movimientos válidos en el archivo de MercadoPago.'))

        transactions.sort(key=lambda vals: (vals['date'], vals['source_idx']))
        statement_vals = {
            'name': _('MercadoPago desde %s hasta %s') % (
                transactions[0]['date'].strftime('%Y-%m-%d'),
                transactions[-1]['date'].strftime('%Y-%m-%d'),
            ),
            'date': transactions[-1]['date'],
            'ponton_import_source': 'mercadopago',
            'transactions': [
                {key: value for key, value in transaction.items() if key != 'source_idx'}
                for transaction in transactions
            ],
        }
        return 'ARS', None, [statement_vals]

    def _get_import_journal(self):
        journal_id = (
            self.env.context.get('journal_id')
            or self.env.context.get('default_journal_id')
            or (
                self.env.context.get('active_id')
                if self.env.context.get('active_model') == 'account.journal'
                else False
            )
        )
        if isinstance(journal_id, (list, tuple)):
            journal_id = journal_id[0] if journal_id else False
        return self.env['account.journal'].browse(journal_id).exists() if journal_id else self.env['account.journal']

    @staticmethod
    def _find_macro_header(rows):
        for idx, row in enumerate(rows):
            normalized = [AccountBankStatementImport._normalize_header(value) for value in row]
            required = {'fecha', 'nro de referencia', 'causal', 'concepto', 'importe'}
            if required.issubset(set(normalized)):
                return idx
        return None

    @staticmethod
    def _find_mp_header(rows):
        for idx, row in enumerate(rows):
            normalized = [AccountBankStatementImport._normalize_header(value) for value in row]
            required = {'fecha de pago', 'tipo de operación', 'número de movimiento', 'operación relacionada', 'importe'}
            if required.issubset(set(normalized)):
                return idx
        return None

    @staticmethod
    def _macro_colmap(header):
        normalized = [AccountBankStatementImport._normalize_header(value) for value in header]
        return {
            'date': normalized.index('fecha'),
            'reference': normalized.index('nro de referencia'),
            'causal': normalized.index('causal'),
            'concept': normalized.index('concepto'),
            'amount': normalized.index('importe'),
            'balance': normalized.index('saldo') if 'saldo' in normalized else None,
        }

    @staticmethod
    def _mp_colmap(header):
        normalized = [AccountBankStatementImport._normalize_header(value) for value in header]
        return {
            'payment_date': normalized.index('fecha de pago'),
            'operation_type': normalized.index('tipo de operación'),
            'movement_number': normalized.index('número de movimiento'),
            'related_operation': normalized.index('operación relacionada'),
            'amount': normalized.index('importe'),
        }

    @staticmethod
    def _find_macro_account_number(rows):
        for row in rows:
            values = [AccountBankStatementImport._to_text(value) for value in row]
            for idx, value in enumerate(values):
                if value.lower() == 'número' and idx + 1 < len(values):
                    for next_value in values[idx + 1:]:
                        if next_value:
                            return next_value
        return None

    @staticmethod
    def _row_has_value(row, col_idx):
        return col_idx is not None and col_idx < len(row) and row[col_idx] not in (None, '')

    @staticmethod
    def _normalize_header(value):
        text = AccountBankStatementImport._to_text(value).lower()
        return ' '.join(text.replace('.', '').split())

    @staticmethod
    def _to_text(value):
        if value is None:
            return ''
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def _to_float(value):
        if value in (None, ''):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace('\xa0', '').replace(' ', '')
        if ',' in text and '.' in text:
            text = text.replace('.', '').replace(',', '.')
        elif ',' in text:
            text = text.replace(',', '.')
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _to_date(value):
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, 'date'):
            return value.date()
        if isinstance(value, str):
            text = value.strip()
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    return datetime.strptime(text[:10], fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _to_mp_datetime(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                return datetime.fromisoformat(text.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

    @staticmethod
    def _mp_local_date(value):
        if value.tzinfo and ZoneInfo:
            return value.astimezone(ZoneInfo('America/Asuncion')).date()
        return value.date()

    @staticmethod
    def _build_note(reference, causal, concept, balance):
        parts = [
            _('Referencia: %s') % reference if reference else '',
            _('Causal: %s') % causal if causal else '',
            _('Concepto original: %s') % concept,
            _('Saldo informado: %.2f') % balance if balance is not None else '',
        ]
        return '\n'.join(part for part in parts if part)

    @staticmethod
    def _mp_line_name(operation_type, related_operation, movement_number):
        if related_operation:
            return 'MP %s - Op %s' % (operation_type, related_operation)
        return 'MP %s - Mov %s' % (operation_type, movement_number)

    @staticmethod
    def _mp_note(payment_date, operation_type, movement_number, related_operation):
        parts = [
            _('Fecha MP: %s') % payment_date.isoformat(),
            _('Tipo MP: %s') % operation_type,
            _('Movimiento MP: %s') % movement_number if movement_number else '',
            _('Operación relacionada MP: %s') % related_operation if related_operation else '',
        ]
        return '\n'.join(part for part in parts if part)

    @staticmethod
    def _unique_import_id(account_number, date, reference, causal, concept, amount):
        raw = '|'.join([
            'macro',
            account_number or '',
            date.isoformat(),
            reference or '',
            causal or '',
            concept or '',
            '%.2f' % amount,
        ])
        return 'macro:%s' % hashlib.sha1(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def _mp_unique_import_id(movement_number, related_operation, operation_type, amount):
        raw = '|'.join([
            'mercadopago',
            movement_number or '',
            related_operation or '',
            operation_type or '',
            '%.2f' % amount,
        ])
        return 'mp:%s' % hashlib.sha1(raw.encode('utf-8')).hexdigest()
