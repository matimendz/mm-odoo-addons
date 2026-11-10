{
    'name': 'El Pontón — Administración y Conciliación',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Cola administrativa para reducir pendientes de conciliación',
    'author': 'Matias Mendez',
    'depends': [
        'account',
        'account_reconcile_oca',
        'mail',
        'ponton_fudo',
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/reconciliation_rule_data.xml',
        'views/reconciliation_issue_views.xml',
        'views/reconciliation_rule_views.xml',
        'views/reconciliation_batch_views.xml',
        'wizards/reconciliation_detect_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}

