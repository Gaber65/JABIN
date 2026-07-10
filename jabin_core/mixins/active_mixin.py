from __future__ import annotations
try:
    from odoo import fields, models
    _ODOO = True
except Exception:
    _ODOO = False
    fields = None
    models = None
if _ODOO:

    class ActiveMixin(models.AbstractModel):
        _name = 'jabin.active.mixin'
        _description = 'JABIN Active Mixin'
        active = fields.Boolean(string='Active', default=True, help='If unchecked, the record is archived and hidden from default searches.')

        def archive(self) -> None:
            self.write({'active': False})

        def unarchive(self) -> None:
            self.write({'active': True})
else:

    class ActiveMixin:
        _name = 'jabin.active.mixin'
        _description = 'JABIN Active Mixin (stub)'