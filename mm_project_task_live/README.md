# mm_project_task_live

Realtime refresh for Odoo Project task views.

When a `project.task` is created, moved, archived, deleted, or changed in a way
that affects kanban/form state, the module publishes a small notification on
Odoo's bus. Open Project task kanban and form views subscribe to that channel and
reload when another browser session changes a relevant task.

## Scope

- Odoo 19.
- Depends on `project`, `bus`, and `web`.
- Sends only minimal metadata: task ids, project ids, stage ids, event type, and
  writing user id.
- Does not grant extra permissions or expose private task fields.

## Install

Add this repository to your Odoo addons path, update the app list, and install:

```bash
odoo -d <database> -i mm_project_task_live
```
