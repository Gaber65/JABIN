# cart_validator.py
from odoo import _
from odoo.exceptions import ValidationError
from typing import Dict, Any, Optional
from odoo.addons.jabin_core import BaseValidator


class CartValidator(BaseValidator):
    """
    Validator for Shopping Cart operations.
    Inherits validation helpers from BaseValidator.
    """

    @staticmethod
    def validate_add_product(vals: Dict[str, Any]) -> None:
        """Validate input for adding a product to the cart."""
        # Require product_id
        CartValidator.validate_required_fields(vals, ['product_id'])

        # Validate product_id is an integer
        CartValidator.validate_field_type(vals['product_id'], int, 'Product ID')

        # Validate quantity if provided
        if 'quantity' in vals:
            CartValidator.validate_positive_number(
                vals['quantity'],
                'Quantity',
                allow_zero=False
            )

    @staticmethod
    def validate_update_quantity(vals: Dict[str, Any]) -> None:
        """Validate input for updating product quantity in the cart."""
        CartValidator.validate_required_fields(vals, ['product_id', 'quantity'])
        CartValidator.validate_field_type(vals['product_id'], int, 'Product ID')
        CartValidator.validate_positive_number(
            vals['quantity'],
            'Quantity',
            allow_zero=False
        )

    @staticmethod
    def validate_checkout(cart) -> None:
        """
        Validate cart state before allowing checkout.
        
        Args:
            cart: The jabin.cart record
        """
        if not cart or not cart.exists():
            raise ValidationError(_("Cart does not exist."))

        if cart.status != 'active':
            raise ValidationError(_("Only active carts can be checked out."))

        if not cart.line_ids:
            raise ValidationError(_("Cannot checkout an empty cart."))

        # Check customer
        customer = cart.customer_id
        if not customer or not customer.exists():
            raise ValidationError(_("Cart has no customer associated."))

        if customer.status not in ('active', 'pending'):
            raise ValidationError(_("Customer is not active."))

        # Check all products in cart
        for line in cart.line_ids:
            product = line.product_id
            if not product or not product.exists():
                raise ValidationError(_("One of the products in the cart does not exist."))
            if not product.active:
                raise ValidationError(_("Product '%s' is inactive.") % product.display_name)
            if not product.is_available:
                raise ValidationError(_("Product '%s' is not available (out of stock).") % product.display_name)
