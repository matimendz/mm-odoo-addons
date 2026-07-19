# AGENTS.md - MM Odoo Addons

This repository owns public Odoo 19 addons on base branch `19.0`.

## Task Workspace And SDD

- Odoo Project is the live task, status, owner and approval source.
- All writes happen in the polyrepo workspace created by `mm-ops`.
- Use branch `agent/odoo-<task-id>-<slug>` based on `19.0`.
- Addon, model, field, view, permission, data or migration changes require a
  complete spec in `specs/<task-id>-<slug>/`.
- Run `task-workspace doctor <task-id> --phase pre-merge` before the PR.
- Never copy databases, filestores, credentials or runtime state.

Run the compile and manifest validation documented in `README.md`.
