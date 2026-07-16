from odoo import api, fields, models, _
from typing import Dict, Any

class ResUsers(models.Model):
    _inherit = 'res.users'

    cart_ids = fields.One2many(
        'jabin.cart',
        'customer_id',
        string='Carts'
    )
    
    active_cart_id = fields.Many2one(
        'jabin.cart',
        compute='_compute_active_cart_id',
        string='Active Cart'
    )
    
    checked_out_cart_ids = fields.One2many(
        'jabin.cart',
        'customer_id',
        domain=[('status', '=', 'checked_out')],
        string='Checked Out Carts'
    )

    def _compute_active_cart_id(self):
        for user in self:
            active_cart = user.cart_ids.filtered(lambda c: c.status == 'active')
            if not active_cart and user.id and user.user_type in ('individual', 'business'):
                # Try to search directly from db to ensure cache is correct
                active_cart = self.env['jabin.cart'].sudo().search([
                    ('customer_id', '=', user.id),
                    ('status', '=', 'active')
                ], limit=1)
                if not active_cart:
                    active_cart = self.env['jabin.cart'].sudo().create({
                        'customer_id': user.id,
                        'currency_id': user.currency_id.id or self.env.company.currency_id.id
                    })
            user.active_cart_id = active_cart[:1]

    def to_public_dict(self) -> Dict[str, Any]:
        """Override to include cart metrics in public user dict."""
        res = super().to_public_dict()
        
        # Access active_cart_id to trigger compute and auto-creation if active user
        active_cart = self.active_cart_id
        
        res.update({
            'active_cart': active_cart.get_summary() if active_cart else None,
            'carts_count': len(self.cart_ids),
            'checked_out_carts_count': len(self.checked_out_cart_ids),
        })
        return res
