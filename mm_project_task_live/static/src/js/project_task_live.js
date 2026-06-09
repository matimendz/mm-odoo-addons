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

function controllerModel(controller) {
    return controller.props?.resModel || controller.model?.root?.resModel;
}

function currentRecordId(controller) {
    return controller.props?.resId || controller.model?.root?.resId;
}

function scheduleReload(controller) {
    if (controller.__mmProjectTaskLiveReload) {
        return;
    }
    controller.notificationService.add("Task board updated in another session", {
        title: "Project live refresh",
        type: "info",
    });
    if (controller.effectService) {
        controller.effectService.add({
            type: "rainbow_man",
            message: "Task moved",
            fadeout: "fast",
        });
    }
    controller.__mmProjectTaskLiveReload = browser.setTimeout(() => {
        controller.__mmProjectTaskLiveReload = null;
        controller.actionService.doAction({ type: "ir.actions.client", tag: "reload" });
    }, 900);
}

function setupProjectTaskLive(controller, mode) {
    controller.busService = useService("bus_service");
    controller.actionService = useService("action");
    controller.effectService = useService("effect");
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
        scheduleReload(controller);
    };

    controller.busService.subscribe(TYPE, controller.__mmProjectTaskLiveHandler);
    onWillDestroy(() => {
        if (controller.__mmProjectTaskLiveReload) {
            browser.clearTimeout(controller.__mmProjectTaskLiveReload);
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
