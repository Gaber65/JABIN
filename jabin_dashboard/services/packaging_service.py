from odoo import _
from odoo.exceptions import ValidationError
from ..validators.packaging_validator import PackagingValidator


class PackagingService:

    @staticmethod
    def create(env, vals):
        PackagingValidator.validate_create(vals)
        return env['jabin.packaging'].create(vals)

    @staticmethod
    def update(env, packaging_id, vals):
        packaging = env['jabin.packaging'].browse(packaging_id)
        if not packaging.exists():
            raise ValidationError(_('Packaging not found!'),)
        PackagingValidator.validate_update(packaging, vals)
        packaging.write(vals)
        return packaging

    @staticmethod
    def delete(env, packaging_id):
        packaging = env['jabin.packaging'].browse(packaging_id)
        if not packaging.exists():
            raise ValidationError(_('Packaging not found!'),)
        packaging.unlink()
        return True

    @staticmethod
    def get(env, packaging_id):
        packaging = env['jabin.packaging'].browse(packaging_id)
        if not packaging.exists():
            raise ValidationError(_('Packaging not found!'),)
        return packaging

    @staticmethod
    def get_all(env, domain=None, limit=None, offset=None):
        domain = domain or []
        return env['jabin.packaging'].search(domain, limit=limit, offset=offset)