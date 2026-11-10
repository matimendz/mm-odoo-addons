import datetime
from collections import defaultdict

from odoo import api, models

AR_TZ = datetime.timezone(datetime.timedelta(hours=-3))


def _fmt_currency(val):
    try:
        return f"${float(val):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _fmt_pct(val):
    try:
        return f"{float(val):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _is_numeric_col(rows, col):
    vals = [str(r[col]) for r in rows if col < len(r)]
    hits = sum(1 for v in vals if v.startswith("$") or v.replace(".", "").replace(",", "").replace("-", "").isdigit())
    return len(vals) > 0 and hits / len(vals) >= 0.5


def _html_table(title, rows, headers):
    if not rows:
        return (
            f'<h3 style="color:#2c3e50;border-bottom:2px solid #e74c3c;padding-bottom:4px">{title}</h3>'
            '<p style="color:#888;font-style:italic">Sin datos en el período.</p>'
        )
    numeric = [_is_numeric_col(rows, i) for i in range(len(headers))]
    th_cells = "".join(
        f'<th style="text-align:{"right" if numeric[i] else "left"}">{h}</th>'
        for i, h in enumerate(headers)
    )
    tbody = ""
    for idx, row in enumerate(rows):
        bg = ' style="background:#f9f9f9"' if idx % 2 == 0 else ""
        tds = "".join(
            f'<td style="text-align:{"right" if (i < len(numeric) and numeric[i]) else "left"}">{cell}</td>'
            for i, cell in enumerate(row)
        )
        tbody += f"<tr{bg}>{tds}</tr>"
    return (
        f'<h3 style="color:#2c3e50;border-bottom:2px solid #e74c3c;padding-bottom:4px">{title}</h3>'
        '<table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:20px">'
        f'<thead><tr style="background:#2c3e50;color:white">{th_cells}</tr></thead>'
        f"<tbody>{tbody}</tbody></table>"
    )


def _html_h2(title):
    return f'<h2 style="color:#e74c3c;margin-top:30px;border-top:3px solid #e74c3c;padding-top:10px">{title}</h2>'


def _html_wrap(period, body):
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 13px; color: #333; max-width: 960px; margin: 0 auto; padding: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 10px; vertical-align: top; }}
    th {{ background: #2c3e50; color: white; font-weight: bold; }}
    .banner {{ background: #2c3e50; color: white; padding: 16px 24px; border-radius: 4px; margin-bottom: 20px; }}
    .banner h1 {{ margin: 0 0 4px; font-size: 20px; }}
    .period {{ color: #aaa; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="banner">
    <h1>Reporte Semanal — El Pontón</h1>
    <span class="period">Período: {period}</span>
  </div>
  {body}
  <hr style="margin-top:40px">
  <p style="color:#999;font-size:11px">Generado automáticamente · ponton_fudo · El Pontón</p>
</body>
</html>"""


class PontonWeeklyReport(models.AbstractModel):
    _name = 'ponton.weekly.report'
    _description = 'Reporte Semanal El Pontón'

    def _week_range(self):
        now = datetime.datetime.now(AR_TZ)
        date_to = now.replace(hour=23, minute=59, second=59, microsecond=0)
        date_from = (date_to - datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0)
        to_utc = lambda d: d.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return to_utc(date_from), to_utc(date_to)

    def _period_label(self, date_from, date_to):
        fmt = lambda d: d.replace(tzinfo=datetime.timezone.utc).astimezone(AR_TZ).strftime("%d/%m/%Y")
        return f"{fmt(date_from)} – {fmt(date_to)}"

    def _query_discounts(self, date_from, date_to):
        SolLine = self.env['sale.order.line']
        lines = SolLine.search([
            ('price_unit', '<', 0),
            ('order_id.date_order', '>=', date_from),
            ('order_id.date_order', '<=', date_to),
            ('order_id.state', 'in', ['sale', 'done']),
        ])
        by_tipo = defaultdict(float)
        by_partner = defaultdict(float)
        by_waiter = defaultdict(float)
        for l in lines:
            tipo = l.product_id.name if l.product_id else 'Descuento Fudo'
            amount = abs(l.price_subtotal)
            by_tipo[tipo] += amount
            partner = l.order_id.partner_id.name if l.order_id.partner_id else 'Sin cliente'
            by_partner[partner] += amount
            waiter = l.order_id.fudo_user_name or 'Sin mozo'
            by_waiter[waiter] += amount
        top_tipo = sorted(by_tipo.items(), key=lambda x: x[1], reverse=True)[:10]
        top_cliente = sorted(by_partner.items(), key=lambda x: x[1], reverse=True)[:10]
        top_mozo = sorted(by_waiter.items(), key=lambda x: x[1], reverse=True)[:10]
        return (
            [[t, _fmt_currency(v)] for t, v in top_tipo],
            [[c, _fmt_currency(v)] for c, v in top_cliente],
            [[w, _fmt_currency(v)] for w, v in top_mozo],
        )

    def _query_ar(self, date_from, date_to):
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', date_from.date()),
            ('invoice_date', '<=', date_to.date()),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('state', '=', 'posted'),
        ])
        totals = defaultdict(float)
        for inv in invoices:
            name = inv.partner_id.name if inv.partner_id else 'Desconocido'
            totals[name] += inv.amount_residual
        top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
        return [[name, _fmt_currency(amt)] for name, amt in top]

    def _query_cancellations(self, date_from, date_to):
        orders = self.env['sale.order'].search([
            ('state', '=', 'cancel'),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
        ])
        rows = []
        for o in orders:
            partner = o.partner_id.name if o.partner_id else '—'
            date = o.date_order.strftime('%Y-%m-%d') if o.date_order else '—'
            products = ', '.join(
                f'{l.product_id.name} ×{l.product_uom_qty:.0f}'
                for l in o.order_line if l.product_id
            ) or '—'
            rows.append([o.name, date, partner, products, _fmt_currency(o.amount_total)])
        return rows

    def _query_expenses(self, date_from, date_to):
        moves = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', date_from.date()),
            ('invoice_date', '<=', date_to.date()),
            ('state', '=', 'posted'),
        ])
        by_account = defaultdict(float)
        by_partner = defaultdict(float)
        for move in moves:
            pname = move.partner_id.name if move.partner_id else 'Sin proveedor'
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                acc = line.account_id.display_name if line.account_id else 'Sin cuenta'
                by_account[acc] += line.price_subtotal
                by_partner[pname] += line.price_subtotal
        top_acc = sorted(by_account.items(), key=lambda x: x[1], reverse=True)[:10]
        top_prov = sorted(by_partner.items(), key=lambda x: x[1], reverse=True)[:10]
        return (
            [[a, _fmt_currency(v)] for a, v in top_acc],
            [[p, _fmt_currency(v)] for p, v in top_prov],
        )

    def _query_sales(self, date_from, date_to):
        orders = self.env['sale.order'].search([
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
        ])
        rev_product = defaultdict(float)
        rev_categ = defaultdict(float)
        rev_partner = defaultdict(float)
        mg_product = defaultdict(lambda: [0.0, 0.0])
        mg_categ = defaultdict(lambda: [0.0, 0.0])
        mg_partner = defaultdict(lambda: [0.0, 0.0])

        for order in orders:
            pname = order.partner_id.name if order.partner_id else 'Sin cliente'
            for l in order.order_line:
                if not l.product_id or l.price_unit < 0:
                    continue
                prod = l.product_id.name
                categ = l.product_id.categ_id.complete_name if l.product_id.categ_id else 'Sin categoría'
                revenue = l.price_subtotal
                pp = getattr(l, 'purchase_price', 0) or 0
                cost = float(pp) * l.product_uom_qty if float(pp) > 0 else (l.product_id.standard_price * l.product_uom_qty)

                rev_product[prod] += revenue
                rev_categ[categ] += revenue
                rev_partner[pname] += revenue
                mg_product[prod][0] += revenue
                mg_product[prod][1] += cost
                mg_categ[categ][0] += revenue
                mg_categ[categ][1] += cost
                mg_partner[pname][0] += revenue
                mg_partner[pname][1] += cost

        def mpct(rv, co):
            return (rv - co) / rv * 100 if rv > 0 else 0.0

        top_rev_prod = sorted(rev_product.items(), key=lambda x: x[1], reverse=True)[:10]
        top_rev_categ = sorted(rev_categ.items(), key=lambda x: x[1], reverse=True)[:10]
        top_rev_partner = sorted(rev_partner.items(), key=lambda x: x[1], reverse=True)[:10]
        top_mg_prod = sorted(mg_product.items(), key=lambda x: mpct(x[1][0], x[1][1]), reverse=True)[:10]
        top_mg_categ = sorted(mg_categ.items(), key=lambda x: mpct(x[1][0], x[1][1]), reverse=True)[:10]
        top_mg_partner = sorted(mg_partner.items(), key=lambda x: mpct(x[1][0], x[1][1]), reverse=True)[:10]
        return (
            [[p, _fmt_currency(v)] for p, v in top_rev_prod],
            [[c, _fmt_currency(v)] for c, v in top_rev_categ],
            [[cl, _fmt_currency(v)] for cl, v in top_rev_partner],
            [[p, _fmt_pct(mpct(v[0], v[1])), _fmt_currency(v[0] - v[1])] for p, v in top_mg_prod],
            [[c, _fmt_pct(mpct(v[0], v[1])), _fmt_currency(v[0] - v[1])] for c, v in top_mg_categ],
            [[cl, _fmt_pct(mpct(v[0], v[1])), _fmt_currency(v[0] - v[1])] for cl, v in top_mg_partner],
        )

    def _get_recipient_emails(self):
        group = self.env.ref('ponton_fudo.group_reporte_semanal', raise_if_not_found=False)
        if not group:
            return []
        users = group.user_ids.filtered(lambda u: u.active and u.email)
        return [u.email for u in users]

    @api.model
    def run(self):
        date_from, date_to = self._week_range()
        period = self._period_label(date_from, date_to)

        disc_tipo, disc_cliente, disc_mozo = self._query_discounts(date_from, date_to)
        ar_rows = self._query_ar(date_from, date_to)
        cancel_rows = self._query_cancellations(date_from, date_to)
        exp_cuenta, exp_proveedor = self._query_expenses(date_from, date_to)
        rev_prod, rev_categ, rev_cliente, mg_prod, mg_categ, mg_cliente = self._query_sales(date_from, date_to)

        body = ""
        body += _html_h2("Descuentos")
        body += _html_table("Top 10 por tipo (nombre Fudo)", disc_tipo, ["Tipo de descuento", "Monto total"])
        body += _html_table("Top 10 por cliente", disc_cliente, ["Cliente", "Monto total"])
        body += _html_table("Top 10 por mozo", disc_mozo, ["Mozo", "Monto total"])

        body += _html_h2("Cuentas Corrientes")
        body += _html_table("Top 10 adiciones del período (facturas sin cobrar)", ar_rows, ["Cliente", "Monto"])

        body += _html_h2("Cancelaciones")
        body += _html_table(
            f"Todas las cancelaciones del período ({len(cancel_rows)})",
            cancel_rows, ["Pedido", "Fecha", "Cliente", "Productos", "Monto"],
        )

        body += _html_h2("Gastos")
        body += _html_table("Top 10 por cuenta contable", exp_cuenta, ["Cuenta", "Monto"])
        body += _html_table("Top 10 por proveedor", exp_proveedor, ["Proveedor", "Monto"])

        body += _html_h2("Ventas")
        body += _html_table("Top 10 por producto (monto)", rev_prod, ["Producto", "Monto"])
        body += _html_table("Top 10 por categoría (monto)", rev_categ, ["Categoría", "Monto"])
        body += _html_table("Top 10 por cliente (monto)", rev_cliente, ["Cliente", "Monto"])
        body += _html_table("Top 10 por producto (margen)", mg_prod, ["Producto", "Margen %", "Ganancia neta"])
        body += _html_table("Top 10 por categoría (margen)", mg_categ, ["Categoría", "Margen %", "Ganancia neta"])
        body += _html_table("Top 10 por cliente (margen)", mg_cliente, ["Cliente", "Margen %", "Ganancia neta"])

        html_body = _html_wrap(period, body)
        subject = f"Reporte Semanal El Pontón — {period}"
        emails = self._get_recipient_emails()
        if not emails:
            return

        self.env['mail.mail'].create({
            'subject': subject,
            'body_html': html_body,
            'email_to': ', '.join(emails),
            'auto_delete': True,
        }).send()
