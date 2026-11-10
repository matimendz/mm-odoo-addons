{
    'name': 'El Pontón — Eventos',
    'version': '19.0.1.0.0',
    'category': 'Events',
    'summary': 'Imagen, tipo de evento y customizaciones de vistas para El Pontón',
    'author': 'Matias Mendez',
    'depends': ['event', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/event_stage_data.xml',
        'views/event_tipo_views.xml',
        'views/event_event_views.xml',
        'views/website_links_templates.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
