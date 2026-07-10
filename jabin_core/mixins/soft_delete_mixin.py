from __future__ import annotations
try:
    from odoo import fields, models
    _ODOO = True
except Exception:
    _ODOO = False
    fields = None
    models = None
if _ODOO:

    class SoftDeleteMixin(models.AbstractModel):
        _name = 'jabin.soft.delete.mixin'
        _description = 'JABIN Soft Delete Mixin'
        is_deleted = fields.Boolean(string='Deleted', default=False, help='Marks the record as soft-deleted (kept for audit).')
        deleted_at = fields.Datetime(string='Deleted At', readonly=True, help='Timestamp at which the record was soft-deleted (UTC).')
        deleted_by = fields.Many2one(comodel_name='jabin.user', string='Deleted By', readonly=True, help='User who soft-deleted the record.')

        def soft_delete(self) -> None:
            vals = {'is_deleted': True, 'deleted_at': fields.Datetime.now(), 'deleted_by': self.env.user.id}
            if 'active' in self._fields:
                vals['active'] = False
            self.write(vals)

        def restore(self) -> None:
            vals = {'is_deleted': False, 'deleted_at': False, 'deleted_by': False}
            if 'active' in self._fields:
                vals['active'] = True
            self.write(vals)
else:

    class SoftDeleteMixin:
        _name = 'jabin.soft.delete.mixin'
        _description = 'JABIN Soft Delete Mixin (stub)'