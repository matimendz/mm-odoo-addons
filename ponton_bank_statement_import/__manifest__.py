{
    'name': 'El Pontón — Importación de Extractos Bancarios',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Importa extractos Excel de Banco Macro para conciliación bancaria',
    'author': 'Matias Mendez',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/account_journal_views.xml',
        'views/account_bank_statement_views.xml',
        'views/account_bank_statement_import_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
