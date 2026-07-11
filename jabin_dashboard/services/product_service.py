from odoo import _
from odoo.exceptions import ValidationError
from ..validators.product_validator import ProductValidator
from datetime import datetime


class ProductService:

    @staticmethod
    def create_product(env, vals):
        """Create a new product with validation"""
        ProductValidator.validate_create(vals)
        product = env['jabin.product'].create(vals)
        return product

    @staticmethod
    def update_product(env, product_id, vals):
        """Update an existing product"""
        product = env['jabin.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found!'), )

        ProductValidator.validate_update(product, vals)
        product.write(vals)
        return product

    @staticmethod
    def delete_product(env, product_id):
        """Delete a product"""
        product = env['jabin.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found!'), )

        product.unlink()
        return True

    @staticmethod
    def get_product(env, product_id):
        """Get a single product"""
        product = env['jabin.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found!'), )
        return product

    @staticmethod
    def get_products(env, domain=None, limit=None, offset=None, order=None):
        """Get list of products with filters"""
        domain = domain or []
        products = env['jabin.product'].search(
            domain,
            limit=limit,
            offset=offset,
            order=order or 'name'
        )
        return products

    @staticmethod
    def get_products_on_offer(env):
        """Get all products currently on offer"""
        today = datetime.now().date()
        domain = [
            ('is_on_offer', '=', True),
            ('offer_start_date', '<=', today),
            ('offer_end_date', '>=', today)
        ]
        return env['jabin.product'].search(domain)

    @staticmethod
    def update_stock(env, product_id, quantity):
        """Update product stock quantity"""
        product = env['jabin.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found!'), )

        if quantity < 0 and abs(quantity) > product.stock_quantity:
            raise ValidationError(_('Insufficient stock!'), )

        product.stock_quantity += quantity
        return product

    @staticmethod
    def toggle_active(env, product_id):
        """Toggle product active status"""
        product = env['jabin.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found!'), )

        product.active = not product.active
        return product
