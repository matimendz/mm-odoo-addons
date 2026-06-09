# mm-odoo-addons

Public Odoo addons maintained by Matias Mendez.

The default branch is `19.0`. Addons in this repository target Odoo 19 unless a
module README says otherwise.

## Addons

- `mm_project_task_live`: realtime refresh for Project task kanban/form views
  when tasks move or change in another browser session.

## Development

Run lightweight validation from the repository root:

```bash
python3 -m compileall .
python3 - <<'PY'
from pathlib import Path
import ast

for manifest in Path(".").glob("*/__manifest__.py"):
    ast.literal_eval(manifest.read_text())
print("manifests ok")
PY
```
