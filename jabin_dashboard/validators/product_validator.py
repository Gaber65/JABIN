from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.jabin_core  import BaseValidator, ValidationUtils
from datetime import datetime


class ProductValidator:
    """Product validator using jabin_core infrastructure"""

    @staticmethod
    def validate_create(vals):
        """Validate product creation data"""
        # Required fields validation using core
        ValidationUtils.validate_required_fields(
            vals,
            ['name', 'sku', 'category_id', 'purchase_price', 'selling_price']
        )

        # Validate SKU format using core
        if 'sku' in vals:
            ValidationUtils.validate_string_format(
                vals['sku'],
                'SKU',
                pattern=r'^[A-Z0-9\-_]+$'
            )

        # Validate positive numbers using core
        if 'purchase_price' in vals:
            ValidationUtils.validate_positive_number(vals['purchase_price'], 'Purchase Price')

        if 'selling_price' in vals:
            ValidationUtils.validate_positive_number(vals['selling_price'], 'Selling Price')

        if 'stock_quantity' in vals:
            ValidationUtils.validate_positive_number(vals['stock_quantity'], 'Stock Quantity')

        # Validate date ranges for offers
        if 'offer_start_date' in vals and 'offer_end_date' in vals:
            if vals['offer_start_date'] and vals['offer_end_date']:
                if vals['offer_start_date'] > vals['offer_end_date']:
                    raise ValidationError(_('Offer start date cannot be after end date!'))

    @staticmethod
    def validate_update(product, vals):
        """Validate product update data"""
        # Validate SKU uniqueness
        if 'sku' in vals:
            if product.env['jabin.product'].search_count([
                ('sku', '=', vals['sku']),
                ('id', '!=', product.id)
            ]) > 0:
                raise ValidationError(_('SKU must be unique!'))

            ValidationUtils.validate_string_format(
                vals['sku'],
                'SKU',
                pattern=r'^[A-Z0-9\-_]+$'
            )

        # Validate barcode uniqueness
        if 'barcode' in vals and vals['barcode']:
            if product.env['jabin.product'].search_count([
                ('barcode', '=', vals['barcode']),
                ('id', '!=', product.id)
            ]) > 0:
                raise ValidationError(_('Barcode must be unique!'))

        # Validate positive numbers
        if 'purchase_price' in vals:
            ValidationUtils.validate_positive_number(vals['purchase_price'], 'Purchase Price')

        if 'selling_price' in vals:
            ValidationUtils.validate_positive_number(vals['selling_price'], 'Selling Price')

        if 'stock_quantity' in vals:
            ValidationUtils.validate_positive_number(vals['stock_quantity'], 'Stock Quantity')

        if 'minimum_stock' in vals:
            ValidationUtils.validate_positive_number(vals['minimum_stock'], 'Minimum Stock')

        # Validate date ranges
        if 'offer_start_date' in vals or 'offer_end_date' in vals:
            start_date = vals.get('offer_start_date', product.offer_start_date)
            end_date = vals.get('offer_end_date', product.offer_end_date)
            if start_date and end_date and start_date > end_date:
                raise ValidationError(_('Offer start date cannot be after end date!'))