{
    'name': 'El Pontón — Integración Fudo',
    'version': '15.0.1.1.0',
    'category': 'Sales',
    'summary': 'Clasificación de ventas Fudo por tipo de noche en pedidos de venta y eventos',
    'author': 'Matias Mendez',
    'depends': ['sale_management', 'event'],
    'data': [
        'views/sale_order_views.xml',
        'views/event_event_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
