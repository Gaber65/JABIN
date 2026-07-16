from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class JabinCart(models.Model):
    _name = 'jabin.cart'
    _description = 'JABIN Shopping Cart'
    _order = 'id desc'

    # --- Core Fields ---
    customer_id = fields.Many2one(
        'res.users',
        string='Customer',
        required=True,
        index=True,
        ondelete='cascade',
        domain="[('user_type', 'in', ['individual', 'business'])]"
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    ], string='Status', default='active', required=True, index=True)

    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        required=True,
        readonly=True
    )
    updated_date = fields.Datetime(
        string='Updated Date',
        default=fields.Datetime.now,
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True
    )


    delivery_address_id = fields.Many2one(
        'res.users.address',
        string='Delivery Address'
    )
    notes = fields.Text(string='Notes')

    # --- Computed Fields ---
    line_ids = fields.One2many(
        'jabin.cart.line',
        'cart_id',
        string='Cart Lines',
        copy=True
    )

    line_count = fields.Integer(
        string='Line Count',
        compute='_compute_line_count',
        store=True
    )
    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_totals',
        store=True
    )
    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    grand_total = fields.Monetary(
        string='Grand Total',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )

    checked_out_order_id = fields.Many2one(
        'jabin.order',
        string='Checked Out Order',
        readonly=True
    )

    # --- Computed Methods ---
    @api.depends('line_ids')
    def _compute_line_count(self):
        for cart in self:
            cart.line_count = len(cart.line_ids)

    @api.depends('line_ids.price_subtotal', 'line_ids.discount_amount',
                 'line_ids.tax_amount')
    def _compute_totals(self):
        for cart in self:
            lines = cart.line_ids
            cart.subtotal = sum(lines.mapped('price_subtotal'))
            cart.discount_amount = sum(lines.mapped('discount_amount'))
            cart.tax_amount = sum(lines.mapped('tax_amount'))
            cart.total_quantity = sum(lines.mapped('quantity'))
            cart.grand_total = cart.subtotal - cart.discount_amount + cart.tax_amount

    # --- ORM Overrides ---
    def write(self, vals):
        """Update updated_date on any write."""
        if 'updated_date' not in vals:
            vals['updated_date'] = fields.Datetime.now()
        return super().write(vals)

    def unlink(self):
        """Prevent deletion of checked out carts."""
        for cart in self:
            if cart.status == 'checked_out':
                raise ValidationError(
                    _("Cannot delete a checked out cart.")
                )
        return super().unlink()

    # --- Business Methods ---
    def _check_modifiable(self):
        self.ensure_one()
        if self.status != 'active':
            raise ValidationError(
                _("Only active carts can be modified.")
            )

    def add_product(self, product_id, quantity=1.0):
        """Add a product to the cart or update quantity if it exists."""
        self.ensure_one()
        self._check_modifiable()
        
        if quantity <= 0:
            raise ValidationError(_("Quantity must be greater than zero."))
            
        product = self.env['jabin.product'].sudo().browse(product_id)
        if not product.exists():
            raise ValidationError(_("Product not found."))
        if not product.active:
            raise ValidationError(_("Product is inactive."))
        if not product.is_available:
            raise ValidationError(_("Product is not available."))

        existing_line = self.line_ids.filtered(lambda l: l.product_id.id == product_id)
        if existing_line:
            existing_line.write({'quantity': existing_line.quantity + quantity})
        else:
            # Determine discount percent
            discount = 0.0
            if product.is_on_offer:
                if product.discount_type == 'percentage':
                    discount = product.discount_value
                elif product.discount_type == 'fixed' and product.selling_price:
                    discount = (product.discount_value / product.selling_price) * 100.0
            
            self.env['jabin.cart.line'].sudo().create({
                'cart_id': self.id,
                'product_id': product_id,
                'quantity': quantity,
                'price_unit': product.selling_price,
                'discount_percent': discount,
                'tax_percent': 0.0
            })
            
        self.write({'updated_date': fields.Datetime.now()})
        return self

    def remove_product(self, product_id):
        """Remove a product from the cart."""
        self.ensure_one()
        self._check_modifiable()
        
        line = self.line_ids.filtered(lambda l: l.product_id.id == product_id)
        if line:
            line.unlink()
            
        self.write({'updated_date': fields.Datetime.now()})
        return self

    def update_quantity(self, product_id, quantity):
        """Update product quantity in the cart."""
        self.ensure_one()
        self._check_modifiable()
        
        if quantity <= 0:
            raise ValidationError(_("Quantity must be greater than zero."))

        product = self.env['jabin.product'].sudo().browse(product_id)
        if not product.exists():
            raise ValidationError(_("Product not found."))
            
        existing_line = self.line_ids.filtered(lambda l: l.product_id.id == product_id)
        if existing_line:
            existing_line.write({'quantity': quantity})
        else:
            if not product.active:
                raise ValidationError(_("Product is inactive."))
            if not product.is_available:
                raise ValidationError(_("Product is not available."))
                
            discount = 0.0
            if product.is_on_offer:
                if product.discount_type == 'percentage':
                    discount = product.discount_value
                elif product.discount_type == 'fixed' and product.selling_price:
                    discount = (product.discount_value / product.selling_price) * 100.0
                    
            self.env['jabin.cart.line'].sudo().create({
                'cart_id': self.id,
                'product_id': product_id,
                'quantity': quantity,
                'price_unit': product.selling_price,
                'discount_percent': discount,
                'tax_percent': 0.0
            })
            
        self.write({'updated_date': fields.Datetime.now()})
        return self

    def increase_quantity(self, product_id):
        """Increase product quantity by 1."""
        self.ensure_one()
        self._check_modifiable()
        
        existing_line = self.line_ids.filtered(lambda l: l.product_id.id == product_id)
        if existing_line:
            existing_line.write({'quantity': existing_line.quantity + 1.0})
            self.write({'updated_date': fields.Datetime.now()})
        else:
            self.add_product(product_id, 1.0)
        return self

    def decrease_quantity(self, product_id):
        """Decrease product quantity by 1."""
        self.ensure_one()
        self._check_modifiable()
        
        existing_line = self.line_ids.filtered(lambda l: l.product_id.id == product_id)
        if existing_line:
            if existing_line.quantity > 1.0:
                existing_line.write({'quantity': existing_line.quantity - 1.0})
            else:
                existing_line.unlink()
            self.write({'updated_date': fields.Datetime.now()})
        return self

    def clear_cart(self):
        """Clear all items from the cart."""
        self.ensure_one()
        self._check_modifiable()
        self.line_ids.unlink()
        self.write({'updated_date': fields.Datetime.now()})
        return self

    def checkout(self):
        """Checkout the cart and create an order."""
        self.ensure_one()
        self._check_modifiable()
        
        if not self.line_ids:
            raise ValidationError(_("Cannot checkout an empty cart."))
            
        if not self.customer_id:
            raise ValidationError(_("Cart has no customer associated."))
            
        if self.customer_id.status not in ('active', 'pending'):
            raise ValidationError(_("Customer is not active."))
            
        for line in self.line_ids:
            if not line.product_id.active:
                raise ValidationError(_("Product %s is not active.") % line.product_id.name)
            if not line.product_id.is_available:
                raise ValidationError(_("Product %s is not available (out of stock).") % line.product_id.name)

        # Create order
        order_vals = {
            'customer_id': self.customer_id.id,
            'date': fields.Datetime.now(),
            'state': 'draft',
            'payment_status': 'pending',
            'currency_id': self.currency_id.id,
            'cart_id': self.id,
        }
        order = self.env['jabin.order'].sudo().create(order_vals)
        
        # Create order lines
        for line in self.line_ids:
            self.env['jabin.order.line'].sudo().create({
                'order_id': order.id,
                'name': line.product_id.display_name,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'discount': line.discount_percent
            })
            
        # Update cart status
        self.write({
            'status': 'checked_out',
            'checked_out_order_id': order.id
        })
        
        # Log customer activity
        self.customer_id.log_activity('checked_out', related_record=f'jabin.order,{order.id}')
        
        return order

    def get_summary(self):
        """Get cart summary as a dictionary."""
        self.ensure_one()
        return {
            'id': self.id,
            'status': self.status,
            'line_count': self.line_count,
            'total_quantity': self.total_quantity,
            'subtotal': self.subtotal,
            'discount_amount': self.discount_amount,
            'tax_amount': self.tax_amount,
            'grand_total': self.grand_total,
            'currency_id': self.currency_id.id if self.currency_id else None,
            'currency_symbol': self.currency_id.symbol if self.currency_id else None,
            'lines': self.line_ids.get_summary_lines()
        }


class JabinCartLine(models.Model):
    _name = 'jabin.cart.line'
    _description = 'JABIN Cart Line'
    _order = 'id asc'

    # --- Core Fields ---
    cart_id = fields.Many2one(
        'jabin.cart',
        string='Cart',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        'jabin.product',
        string='Product',
        required=True,
        ondelete='restrict',
        index=True
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True
    )

    # --- Price Fields (snapshot from product at add time) ---
    price_unit = fields.Float(
        string='Unit Price',
        required=True,
        default=0.0
    )
    discount_percent = fields.Float(
        string='Discount (%)',
        default=0.0
    )
    tax_percent = fields.Float(
        string='Tax (%)',
        default=0.0
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='cart_id.currency_id',
        store=True,
        readonly=True
    )

    # --- Computed Fields ---
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_line_totals',
        store=True,
        currency_field='currency_id'
    )
    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_line_totals',
        store=True,
        currency_field='currency_id'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount',
        compute='_compute_line_totals',
        store=True,
        currency_field='currency_id'
    )
    line_total = fields.Monetary(
        string='Line Total',
        compute='_compute_line_totals',
        store=True,
        currency_field='currency_id'
    )

    # --- Computed Methods ---
    @api.depends('price_unit', 'quantity', 'discount_percent', 'tax_percent')
    def _compute_line_totals(self):
        for line in self:
            base = line.price_unit * line.quantity
            line.discount_amount = base * (line.discount_percent / 100.0)
            line.price_subtotal = base - line.discount_amount
            line.tax_amount = line.price_subtotal * (line.tax_percent / 100.0)
            line.line_total = line.price_subtotal + line.tax_amount

    # --- ORM Overrides ---
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    _("Quantity must be greater than zero.")
                )

    # --- Business Methods ---
    def get_summary_line(self):
        """Get line summary as a dictionary."""
        self.ensure_one()
        return {
            'id': self.id,
            'product_id': self.product_id.id,
            'product_name': self.product_id.display_name,
            'product_image': self.product_id.image_1920 if hasattr(self.product_id, 'image_1920') else None,
            'quantity': self.quantity,
            'price_unit': self.price_unit,
            'discount_percent': self.discount_percent,
            'tax_percent': self.tax_percent,
            'price_subtotal': self.price_subtotal,
            'discount_amount': self.discount_amount,
            'tax_amount': self.tax_amount,
            'line_total': self.line_total,
        }

    def get_summary_lines(self):
        """Get summary for all lines."""
        return [line.get_summary_line() for line in self]