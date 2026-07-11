from odoo import _
from odoo.exceptions import ValidationError
from ..validators.cutting_option_validator import CuttingOptionValidator


class CuttingOptionService:

    @staticmethod
    def create(env, vals):
        CuttingOptionValidator.validate_create(vals)
        return env['jabin.cutting.option'].create(vals)

    @staticmethod
    def update(env, option_id, vals):
        option = env['jabin.cutting.option'].browse(option_id)
        if not option.exists():
            raise ValidationError(_('Cutting Option not found!'), )
        CuttingOptionValidator.validate_update(option, vals)
        option.write(vals)
        return option

    @staticmethod
    def delete(env, option_id):
        option = env['jabin.cutting.option'].browse(option_id)
        if not option.exists():
            raise ValidationError(_('Cutting Option not found!'), )
        option.unlink()
        return True

    @staticmethod
    def get(env, option_id):
        option = env['jabin.cutting.option'].browse(option_id)
        if not option.exists():
            raise ValidationError(_('Cutting Option not found!'), )
        return option

    @staticmethod
    def get_all(env, domain=None, limit=None, offset=None):
        domain = domain or []
        return env['jabin.cutting.option'].search(domain, limit=limit, offset=offset)