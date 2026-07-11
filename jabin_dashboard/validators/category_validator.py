from odoo import _
from odoo.exceptions import ValidationError
# Import validation utilities from odoo.addons.jabin_core 
from odoo.addons.jabin_core  import  ValidationUtils


class CategoryValidator:
    """Category validator using jabin_core infrastructure"""

    @staticmethod
    def validate_create(vals):
        """Validate category creation data"""
        # Use core validation utilities
        ValidationUtils.validate_required_fields(vals, ['name'])

        # Validate name length
        if 'name' in vals:
            ValidationUtils.validate_string_length(vals['name'], 'Name', min_length=2, max_length=100)

    @staticmethod
    def validate_update(category, vals):
        """Validate category update data"""
        if 'name' in vals:
            # Use core validation for unique fields
            if category.env['jabin.category'].search_count([
                ('name', '=', vals['name']),
                ('id', '!=', category.id)
            ]) > 0:
                raise ValidationError(_('Category name must be unique!'))

            ValidationUtils.validate_string_length(vals['name'], 'Name', min_length=2, max_length=100)