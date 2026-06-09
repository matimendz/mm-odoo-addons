from odoo import api, models


LIVE_CHANNEL = "mm_project_task_live"
LIVE_FIELDS = {
    "active",
    "date_deadline",
    "kanban_state",
    "planned_date_begin",
    "priority",
    "project_id",
    "sequence",
    "stage_id",
    "user_ids",
}


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _mm_live_payload(self, event, changed_fields=None):
        tasks = self.exists()
        return {
            "event": event,
            "model": "project.task",
            "task_ids": tasks.ids,
            "project_ids": tasks.mapped("project_id").ids,
            "stage_ids": tasks.mapped("stage_id").ids,
            "changed_fields": sorted(changed_fields or []),
            "write_uid": self.env.uid,
        }

    def _mm_notify_live_update(self, event, changed_fields=None):
        payload = self._mm_live_payload(event, changed_fields)
        self.env["bus.bus"]._sendone(LIVE_CHANNEL, "project_task_live_update", payload)

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._mm_notify_live_update("create", set().union(*(vals.keys() for vals in vals_list)))
        return tasks

    def write(self, vals):
        changed_fields = set(vals)
        should_notify = bool(changed_fields & LIVE_FIELDS)
        result = super().write(vals)
        if should_notify:
            self._mm_notify_live_update("write", changed_fields)
        return result

    def unlink(self):
        payload = self._mm_live_payload("unlink", {"active"})
        result = super().unlink()
        self.env["bus.bus"]._sendone(LIVE_CHANNEL, "project_task_live_update", payload)
        return result
