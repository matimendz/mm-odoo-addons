{
    "name": "Project Task Live Refresh",
    "version": "19.0.1.0.0",
    "category": "Project",
    "summary": "Realtime refresh for Project task kanban and form views.",
    "author": "Matias Mendez",
    "website": "https://github.com/matimendz/mm-odoo-addons",
    "license": "LGPL-3",
    "depends": [
        "bus",
        "project",
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            "mm_project_task_live/static/src/js/project_task_live.js",
        ],
    },
    "installable": True,
    "application": False,
}
