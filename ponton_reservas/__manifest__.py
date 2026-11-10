{
    'name': 'El Pontón — Reservas',
    'version': '19.0.1.0.0',
    'category': 'Operations',
    'summary': 'Gestión de reservas de El Pontón sin dependencia de Odoo Studio',
    'author': 'Matias Mendez',
    'depends': ['contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/ponton_reserva_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
