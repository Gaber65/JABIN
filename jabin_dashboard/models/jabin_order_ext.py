from odoo import fields, models

class JabinOrder(models.Model):
    _inherit = 'jabin.order'

    cart_id = fields.Many2one(
        'jabin.cart',
        string='Source Cart',
        readonly=True,
        ondelete='restrict'
    )
