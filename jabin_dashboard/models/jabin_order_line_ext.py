from odoo import fields, models

class JabinOrderLine(models.Model):
    _inherit = "jabin.order.line"

    product_id = fields.Many2one(
        "jabin.product",
        string="Product",
        required=True,
        ondelete="restrict"
    )
