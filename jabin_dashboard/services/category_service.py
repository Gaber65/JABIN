from odoo import _
from odoo.exceptions import ValidationError
from ..validators.category_validator import CategoryValidator


class CategoryService:
    """Category service using jabin_core infrastructure"""

    @staticmethod
    def create_category(env, vals):
        """Create a new category with validation"""
        CategoryValidator.validate_create(vals)
        category = env['jabin.category'].create(vals)
        return category

    @staticmethod
    def update_category(env, category_id, vals):
        """Update an existing category"""
        category = env['jabin.category'].browse(category_id)
        if not category.exists():
            raise ValidationError(_('Category not found!'), )

        CategoryValidator.validate_update(category, vals)
        category.write(vals)
        return category

    @staticmethod
    def delete_category(env, category_id):
        """Delete a category if no products exist"""
        category = env['jabin.category'].browse(category_id)
        if not category.exists():
            raise ValidationError(_('Category not found!'), )

        if category.product_ids:
            raise ValidationError(
                _('Cannot delete category with existing products!'),
            )

        category.unlink()
        return True

    @staticmethod
    def get_category(env, category_id):
        """Get a single category"""
        category = env['jabin.category'].browse(category_id)
        if not category.exists():
            raise ValidationError(_('Category not found!'), )
        return category

    @staticmethod
    def get_categories(env, domain=None, limit=None, offset=None, order=None):
        """Get list of categories with filters"""
        domain = domain or []
        categories = env['jabin.category'].search(
            domain,
            limit=limit,
            offset=offset,
            order=order or 'sequence, name'
        )
        return categories
