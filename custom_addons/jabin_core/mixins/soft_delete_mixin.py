# -*- coding: utf-8 -*-
"""Soft-delete mixin for the JABIN platform (PREPARED ONLY).

Soft deletion keeps records in the database (for audit / referential integrity)
but marks them as deleted so they are excluded from normal queries. This is
critical for an e-commerce ERP where orders, payments and invoices must never
be truly removed.

Sprint 1 scope
--------------
This mixin is **prepared but not fully active**: it declares the fields and the
``soft_delete`` / ``restore`` methods, but it does **not** yet override the
default search domain to exclude soft-deleted records automatically. That
override is intentionally deferred to the sprint where the first soft-deletable
business model is introduced, because auto-filtering must be opt-in per model
to avoid breaking Odoo's internal queries (e.g. copying, reporting).

Fields
------
``is_deleted``  Boolean, default ``False``.
``deleted_at``  Datetime, set when ``soft_delete`` is called.
``deleted_by``  Many2one -> ``res.users``, set when ``soft_delete`` is called.

Usage
-----
::

    class MyModel(models.Model):
        _name = "jabin.thing"
        _inherit = ["jabin.active.mixin", "jabin.soft.delete.mixin"]

Future work (post Sprint 1)
---------------------------
* Override ``search`` to inject ``[("is_deleted", "=", False)]`` when the
  context key ``active_soft_delete_test`` is not explicitly disabled.
* Override ``unlink`` to convert to ``soft_delete()`` for models that should
  never be hard-deleted.
* Add a ``hard_delete`` admin-only method for genuine purging under retention
  policies.
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

    class SoftDeleteMixin(models.AbstractModel):
        """Soft-deletion fields and helpers (prepared, not auto-filtering yet)."""

        _name = "jabin.soft.delete.mixin"
        _description = "JABIN Soft Delete Mixin"

        is_deleted = fields.Boolean(
            string="Deleted",
            default=False,
            help="Marks the record as soft-deleted (kept for audit).",
        )
        deleted_at = fields.Datetime(
            string="Deleted At",
            readonly=True,
            help="Timestamp at which the record was soft-deleted (UTC).",
        )
        deleted_by = fields.Many2one(
            comodel_name="res.users",
            string="Deleted By",
            readonly=True,
            help="User who soft-deleted the record.",
        )

        # ------------------------------------------------------------------ #
        # Public helpers
        # ------------------------------------------------------------------ #
        def soft_delete(self) -> None:
            """Mark the current recordset as soft-deleted.

            Also archives the record (``active=False``) if the model also
            inherits :class:`ActiveMixin`, so it disappears from default
            searches immediately.
            """
            vals = {
                "is_deleted": True,
                "deleted_at": fields.Datetime.now(),
                "deleted_by": self.env.user.id,
            }
            # Archive too if the active field exists on the model.
            if "active" in self._fields:
                vals["active"] = False
            self.write(vals)

        def restore(self) -> None:
            """Restore a soft-deleted recordset."""
            vals = {
                "is_deleted": False,
                "deleted_at": False,
                "deleted_by": False,
            }
            if "active" in self._fields:
                vals["active"] = True
            self.write(vals)

else:  # pragma: no cover

    class SoftDeleteMixin:  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""

        _name = "jabin.soft.delete.mixin"
        _description = "JABIN Soft Delete Mixin (stub)"
