# -*- coding: utf-8 -*-
"""Active mixin for the JABIN platform.

Adds an ``active`` boolean flag plus ``archive`` / ``unarchive`` helper methods
to any model. Odoo's ORM automatically excludes records where ``active=False``
from searches (the ``active_test`` context flag toggles this), so simply
declaring the field gives us archive/unarchive semantics for free.

This mixin centralises the field declaration and provides clean, documented
action methods that controllers/services can call without reaching into raw
field manipulation.

Usage
-----
::

    class MyModel(models.Model):
        _name = "jabin.thing"
        _inherit = ["jabin.active.mixin"]

Extensibility
-------------
* A future ``SoftDeleteMixin`` builds on top of this by adding a hard delete
  timestamp while keeping the record archived.
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

    class ActiveMixin(models.AbstractModel):
        """Provide an ``active`` flag with archive/unarchive helpers."""

        _name = "jabin.active.mixin"
        _description = "JABIN Active Mixin"

        active = fields.Boolean(
            string="Active",
            default=True,
            help="If unchecked, the record is archived and hidden from "
                 "default searches.",
        )

        # ------------------------------------------------------------------ #
        # Public helpers
        # ------------------------------------------------------------------ #
        def archive(self) -> None:
            """Archive the current recordset (set ``active=False``)."""
            self.write({"active": False})

        def unarchive(self) -> None:
            """Restore the current recordset (set ``active=True``)."""
            self.write({"active": True})

else:  # pragma: no cover

    class ActiveMixin:  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""

        _name = "jabin.active.mixin"
        _description = "JABIN Active Mixin (stub)"
