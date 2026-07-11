from odoo import _
from odoo.exceptions import ValidationError
from ..validators.excluded_part_validator import ExcludedPartValidator


class ExcludedPartService:

    @staticmethod
    def create(env, vals):
        ExcludedPartValidator.validate_create(vals)
        return env['jabin.excluded.part'].create(vals)

    @staticmethod
    def update(env, part_id, vals):
        part = env['jabin.excluded.part'].browse(part_id)
        if not part.exists():
            raise ValidationError(_('Excluded Part not found!'), )
        ExcludedPartValidator.validate_update(part, vals)
        part.write(vals)
        return part

    @staticmethod
    def delete(env, part_id):
        part = env['jabin.excluded.part'].browse(part_id)
        if not part.exists():
            raise ValidationError(_('Excluded Part not found!'), )
        part.unlink()
        return True

    @staticmethod
    def get(env, part_id):
        part = env['jabin.excluded.part'].browse(part_id)
        if not part.exists():
            raise ValidationError(_('Excluded Part not found!'), )
        return part

    @staticmethod
    def get_all(env, domain=None, limit=None, offset=None):
        domain = domain or []
        return env['jabin.excluded.part'].search(domain, limit=limit, offset=offset)
