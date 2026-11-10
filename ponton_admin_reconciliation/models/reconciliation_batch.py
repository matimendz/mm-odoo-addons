from odoo import fields, models


class PontonReconciliationBatch(models.Model):
    _name = 'ponton.reconciliation.batch'
    _description = 'Corrida de detección de conciliación'
    _inherit = ['mail.thread']
    _order = 'started_at desc, id desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    mode = fields.Selection(
        [
            ('dry_run', 'Dry-run'),
            ('real', 'Real'),
        ],
        default='real',
        required=True,
    )
    started_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    finished_at = fields.Datetime(readonly=True)
    detected_count = fields.Integer(readonly=True)
    created_count = fields.Integer(readonly=True)
    existing_count = fields.Integer(readonly=True)
    suggested_count = fields.Integer(readonly=True)
    applied_count = fields.Integer(readonly=True)
    error_count = fields.Integer(readonly=True)
    notes = fields.Text()
    issue_ids = fields.One2many('ponton.reconciliation.issue', 'batch_id')

