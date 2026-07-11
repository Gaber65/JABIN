from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.jabin_core  import ValidationUtils


class PackagingValidator:

    @staticmethod
    def validate_create(vals):
        ValidationUtils.validate_required_fields(vals, ['name'])
        if 'name' in vals:
            ValidationUtils.validate_string_length(vals['name'], 'Name', min_length=2, max_length=100)

    @staticmethod
    def validate_update(packaging, vals):
        if 'name' in vals:
            if packaging.env['jabin.packaging'].search_count([
                ('name', '=', vals['name']),
                ('id', '!=', packaging.id)
            ]) > 0:
                raise ValidationError(_('Packaging name must be unique!'))
            ValidationUtils.validate_string_length(vals['name'], 'Name', min_length=2, max_length=100)