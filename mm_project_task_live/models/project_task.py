from datetime import date, datetime

from odoo import api, fields, models


LIVE_CHANNEL = "mm_project_task_live"
LIVE_FIELDS = {
    "active",
    "date_deadline",
    "kanban_state",
    "name",
    "planned_date_begin",
    "priority",
    "project_id",
    "sequence",
    "stage_id",
    "user_ids",
}
SNAPSHOT_FIELDS = {
    "active",
    "date_deadline",
    "kanban_state",
    "name",
    "planned_date_begin",
    "priority",
    "project_id",
    "sequence",
    "stage_id",
    "user_ids",
}


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _mm_live_snapshot(self):
        def field_value(task, field_name):
            value = task[field_name]
            if field_name in {"project_id", "stage_id"}:
                return {"id": value.id, "display_name": value.display_name} if value else False
            if field_name == "user_ids":
                return [{"id": user.id, "display_name": user.display_name} for user in value]
            if isinstance(value, (date, datetime)):
                return fields.Datetime.to_string(value)
            return value

        return {
            task.id: {
                field_name: field_value(task, field_name)
                for field_name in SNAPSHOT_FIELDS
                if field_name in task._fields
            }
            for task in self.exists()
        }

    def _mm_live_payload(self, event, changed_fields=None, before=None, after=None):
        tasks = self.exists()
        return {
            "event": event,
            "model": "project.task",
            "task_ids": tasks.ids,
            "project_ids": tasks.mapped("project_id").ids,
            "stage_ids": tasks.mapped("stage_id").ids,
            "changed_fields": sorted(changed_fields or []),
            "write_uid": self.env.uid,
            "tasks": [
                {
                    "id": task.id,
                    "name": task.display_name,
                    "before": (before or {}).get(task.id, {}),
                    "after": (after or {}).get(task.id, {}),
                }
                for task in tasks
            ],
        }

    def _mm_notify_live_update(self, event, changed_fields=None, before=None, after=None):
        payload = self._mm_live_payload(event, changed_fields, before, after)
        self.env["bus.bus"]._sendone(LIVE_CHANNEL, "project_task_live_update", payload)

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._mm_notify_live_update(
            "create",
            set().union(*(vals.keys() for vals in vals_list)),
            after=tasks._mm_live_snapshot(),
        )
        return tasks

    def write(self, vals):
        changed_fields = set(vals)
        should_notify = bool(changed_fields & LIVE_FIELDS)
        before = self._mm_live_snapshot() if should_notify else {}
        result = super().write(vals)
        if should_notify:
            self._mm_notify_live_update(
                "write",
                changed_fields,
                before=before,
                after=self._mm_live_snapshot(),
            )
        return result

    def unlink(self):
        before = self._mm_live_snapshot()
        payload = self._mm_live_payload("unlink", {"active"}, before=before)
        result = super().unlink()
        self.env["bus.bus"]._sendone(LIVE_CHANNEL, "project_task_live_update", payload)
        return result
