from __future__ import annotations
from odoo import fields, models
from odoo.addons.jabin_core import JabinLogger
_logger = JabinLogger.get('security.res_users')

class JabinUserSecurity(models.Model):
    _inherit = 'res.users'
    _description = 'JABIN User Security Extension'
    x_jabin_role_ids = fields.Many2many(comodel_name='jabin.role', relation='jabin_role_user_rel', column1='user_id', column2='role_id', string='JABIN Roles', help='RBAC roles assigned to this user.')

    def get_role_codes(self) -> list:
        self.ensure_one()
        return self.x_jabin_role_ids.mapped('code')

    def get_permission_codes(self) -> set:
        self.ensure_one()
        if not self.x_jabin_role_ids:
            return set()
        perms = self.x_jabin_role_ids.mapped('permission_ids.code')
        return set(perms)