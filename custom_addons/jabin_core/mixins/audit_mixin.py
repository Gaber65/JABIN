# -*- coding: utf-8 -*-
"""Audit mixin for the JABIN platform.

Tracks *who* created and last updated a record, complementing the *when*
provided by :class:`TimestampMixin`. This is essential for compliance,
forensics, and the future audit-log feature.

Fields
------
``created_by``  Many2one -> ``res.users`` ; stamped on ``create``.
``updated_by``  Many2one -> ``res.users`` ; stamped on every ``write``.

Implementation
--------------
The mixin overrides ``create`` and ``write`` to stamp the current user. The
overrides are written so that they:

* Use ``self.env.user`` (works for both interactive and programmatic contexts).
* Always call ``super()`` and return its result unchanged, preserving Odoo's
  own contract.
* Are safe when the model is created by the system user (uid 1) or during
  module install.

Usage
-----
::

    class MyModel(models.Model):
        _name = "jabin.thing"
        _inherit = ["jabin.timestamp.mixin", "jabin.audit.mixin"]

Extensibility
-------------
* When JWT auth lands, the "current user" can be resolved from the token
  instead of ``self.env.user``; the override point is right here.
"""

from __future__ import annotations

try:
    from odoo import fields, models  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover
    _ODOO = False
    fields = None  # type: ignore
    models = None  # type: ignore


if _ODOO:

    class AuditMixin(models.AbstractModel):
        """Track the user who created / last updated each record."""

        _name = "jabin.audit.mixin"
        _description = "JABIN Audit Mixin"

        created_by = fields.Many2one(
            comodel_name="res.users",
            string="Created By",
            readonly=True,
            help="User who created the record.",
        )
        updated_by = fields.Many2one(
            comodel_name="res.users",
            string="Last Updated By",
            readonly=True,
            help="User who last updated the record.",
        )

        # ------------------------------------------------------------------ #
        # ORM overrides
        # ------------------------------------------------------------------ #
        def create(self, vals_list):
            """Stamp ``created_by`` / ``updated_by`` on record creation."""
            user_id = self.env.user.id
            # ``vals_list`` may be a dict (single) or list (batch) in Odoo 17.
            if isinstance(vals_list, dict):
                vals_list = dict(vals_list)
                vals_list.setdefault("created_by", user_id)
                vals_list.setdefault("updated_by", user_id)
            else:
                vals_list = [
                    {**vals, "created_by": vals.get("created_by", user_id),
                     "updated_by": vals.get("updated_by", user_id)}
                    for vals in vals_list
                ]
            return super().create(vals_list)

        def write(self, vals):
            """Stamp ``updated_by`` on every write."""
            if "updated_by" not in vals:
                vals = {**vals, "updated_by": self.env.user.id}
            return super().write(vals)

else:  # pragma: no cover

    class AuditMixin:  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""

        _name = "jabin.audit.mixin"
        _description = "JABIN Audit Mixin (stub)"
