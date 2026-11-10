{
    'name': 'El Pontón — Eventos',
    'version': '15.0.1.0.0',
    'category': 'Events',
    'summary': 'Imagen, tipo de evento y customizaciones de vistas para El Pontón',
    'author': 'Matias Mendez',
    'depends': ['event'],
    'data': [
        'security/ir.model.access.csv',
        'views/event_tipo_views.xml',
        'views/event_event_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ponton_event/static/src/css/brand.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
