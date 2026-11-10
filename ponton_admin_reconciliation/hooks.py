from odoo import api, SUPERUSER_ID


def post_init_hook(cr_or_env, registry=None):
    env = cr_or_env if registry is None else api.Environment(cr_or_env, SUPERUSER_ID, {})
    env['ponton.reconciliation.rule']._ensure_identification_account()
