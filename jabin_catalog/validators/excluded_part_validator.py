from odoo import _
from odoo.exceptions import ValidationError
from jabin_core.validators import ValidationUtils


class ExcludedPartValidator:

    @staticmethod
    def validate_create(vals):
        ValidationUtils.validate_required_fields(vals, ['name'])
        if 'name' in vals:
            ValidationUtils.validate_string_length(vals['name'], 'Name', min_length=2, max_length=100)

    @staticmethod
    def validate_update(part, vals):
        if 'name' in vals:
            if part.env['jabin.excluded.part'].search_count([
                ('name', '=', vals['name']),
                ('id', '!=', part.id)
            ]) > 0:
                raise ValidationError(_('Excluded Part name must be unique!'))
            ValidationUtils.validate_string_length(vals['name'], 'Name', min_length=2, max_length=100)