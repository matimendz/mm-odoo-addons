/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { FormController } from "@web/views/form/form_controller";
import { onWillDestroy } from "@odoo/owl";

const CHANNEL = "mm_project_task_live";
const TYPE = "project_task_live_update";
const STAGE_MOVE_DELAY_MS = 850;
const ANIMATION_CLEANUP_MS = 1800;

function controllerModel(controller) {
    return controller.props?.resModel || controller.model?.root?.resModel;
}

function currentRecordId(controller) {
    return controller.props?.resId || controller.model?.root?.resId;
}

function fieldLabel(fieldName) {
    return {
        active: "archivo",
        date_deadline: "fecha limite",
        kanban_state: "estado kanban",
        name: "nombre",
        planned_date_begin: "fecha planificada",
        priority: "prioridad",
        project_id: "proyecto",
        sequence: "orden",
        stage_id: "etapa",
        user_ids: "responsables",
    }[fieldName] || fieldName;
}

function displayValue(value) {
    if (value === false || value === undefined || value === null || value === "") {
        return "vacio";
    }
    if (Array.isArray(value)) {
        return value.map((item) => item.display_name || item.name || item).join(", ") || "vacio";
    }
    if (typeof value === "object") {
        return value.display_name || value.name || JSON.stringify(value);
    }
    return String(value);
}

function taskSummary(payload) {
    const task = payload.tasks?.[0] || {};
    const before = task.before || {};
    const after = task.after || {};
    const fields = payload.changed_fields || [];
    const title = task.name || after.name || before.name || `Tarea #${task.id || ""}`;

    if (payload.event === "create") {
        return `${title} fue creada en ${displayValue(after.stage_id)}`;
    }
    if (payload.event === "unlink") {
        return `${title} fue eliminada o archivada`;
    }
    if (fields.includes("stage_id")) {
        return `${title}: ${displayValue(before.stage_id)} -> ${displayValue(after.stage_id)}`;
    }
    if (fields.includes("name")) {
        return `${displayValue(before.name)} -> ${displayValue(after.name)}`;
    }
    const changed = fields
        .slice(0, 3)
        .map((fieldName) => `${fieldLabel(fieldName)}: ${displayValue(after[fieldName])}`)
        .join(" | ");
    return `${title}: ${changed || "actualizada"}`;
}

function findVisibleTaskElement(controller, task, mode) {
    const root = controller.rootRef?.el;
    if (!task || !root) {
        return null;
    }
    if (mode === "form") {
        return root;
    }
    const selectors = [
        `[data-res-id="${task.id}"]`,
        `[data-record-id="${task.id}"]`,
        `[data-id="${task.id}"]`,
    ];
    const element = selectors.map((selector) => root.querySelector(selector)).find(Boolean);
    if (element) {
        return element;
    }
    const taskName = task.after?.name || task.name || task.before?.name;
    return [...root.querySelectorAll(".o_kanban_record")].find((record) =>
        taskName ? record.textContent.includes(taskName) : false
    );
}

function animateTaskElement(controller, payload, mode, className) {
    const task = payload.tasks?.[0];
    const element = findVisibleTaskElement(controller, task, mode);
    if (!element) {
        return;
    }
    element.classList.remove(
        "mm_project_task_live_entering",
        "mm_project_task_live_highlight",
        "mm_project_task_live_leaving"
    );
    void element.offsetWidth;
    element.classList.add(className);
    element.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
    browser.setTimeout(() => element.classList.remove(className), ANIMATION_CLEANUP_MS);
}

function wait(ms) {
    return new Promise((resolve) => browser.setTimeout(resolve, ms));
}

async function refreshVisibleView(controller, payload, mode) {
    if (controller.__mmProjectTaskLiveReload) {
        return;
    }
    controller.notificationService.add(taskSummary(payload), {
        title: "Tarea actualizada",
        type: "info",
    });
    controller.__mmProjectTaskLiveReload = true;
    try {
        const isStageMove = mode === "kanban" && payload.changed_fields?.includes("stage_id");
        if (isStageMove) {
            animateTaskElement(controller, payload, mode, "mm_project_task_live_leaving");
            await wait(STAGE_MOVE_DELAY_MS);
        }
        if (mode === "form") {
            const resId = currentRecordId(controller);
            await controller.model.load({ resId, resIds: controller.model.root?.resIds });
        } else {
            await controller.model.load();
        }
        controller.render(true);
        browser.setTimeout(
            () =>
                animateTaskElement(
                    controller,
                    payload,
                    mode,
                    isStageMove ? "mm_project_task_live_entering" : "mm_project_task_live_highlight"
                ),
            80
        );
    } finally {
        controller.__mmProjectTaskLiveReload = null;
    }
}

function setupProjectTaskLive(controller, mode) {
    controller.busService = useService("bus_service");
    controller.notificationService = useService("notification");
    controller.busService.addChannel(CHANNEL);

    controller.__mmProjectTaskLiveHandler = (payload) => {
        if (controllerModel(controller) !== "project.task") {
            return;
        }
        if (payload.model !== "project.task") {
            return;
        }
        if (payload.write_uid === session.uid) {
            return;
        }
        if (mode === "form") {
            const resId = currentRecordId(controller);
            if (resId && !payload.task_ids?.includes(resId)) {
                return;
            }
        }
        refreshVisibleView(controller, payload, mode);
    };

    controller.busService.subscribe(TYPE, controller.__mmProjectTaskLiveHandler);
    onWillDestroy(() => {
        if (controller.__mmProjectTaskLiveReload) {
            controller.__mmProjectTaskLiveReload = null;
        }
        controller.busService.unsubscribe(TYPE, controller.__mmProjectTaskLiveHandler);
    });
}

patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        setupProjectTaskLive(this, "kanban");
    },
});

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        setupProjectTaskLive(this, "form");
    },
});
