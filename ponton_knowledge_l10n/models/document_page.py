from odoo import fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    ponton_visibility_group_ids = fields.Many2many(
        "res.groups",
        "ponton_document_page_res_groups_rel",
        "page_id",
        "group_id",
        string="Grupos de visibilidad",
        help=(
            "Si se deja vacio, la pagina queda visible para todos los usuarios "
            "con acceso a Conocimientos. Si se completa, solo la ven usuarios "
            "que pertenezcan a alguno de estos grupos."
        ),
    )
