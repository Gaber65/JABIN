# -*- coding: utf-8 -*-
"""Timestamp mixin for the JABIN platform.

Adds creation and modification timestamps to any model that inherits it.

Odoo already provides ``create_date`` and ``write_date`` on every model via
``mail.thread`` / the base ORM, but:

1. Not every model inherits ``mail.thread`` (and we do not want to force that
   dependency on lightweight lookup tables).
2. We want a **single, documented, importable** place where the timestamp
   contract is declared, so future modules can rely on
   ``from jabin_core.mixins import TimestampMixin`` instead of remembering
   which fields Odoo adds implicitly.

This mixin therefore explicitly (re-)declares the timestamp fields with
``readonly=True`` and ``store=True`` so they are always present, always
readonly from the UI, and always serialised.

Usage
-----
::

    class MyModel(models.Model):
        _name = "jabin.thing"
        _inherit = ["jabin.timestamp.mixin"]

Extensibility
-------------
* A future ``SoftDeleteMixin`` can override ``write`` to stamp ``deleted_at``
  instead of truly deleting the record.
"""

from __future__ import annotations

try:  # Odoo is available at runtime; guard for plain-Python test contexts.
    from odoo import fields, models  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover - non-Odoo environment
    _ODOO = False
    fields = None  # type: ignore
    models = None  # type: ignore


if _ODOO:

    class TimestampMixin(models.AbstractModel):
        """Provide explicit ``create_date`` / ``write_date`` fields.

        These fields are ``readonly`` and automatically populated by the ORM,
        so the mixin only declares them; it does not override ``create`` /
        ``write``.
        """

        _name = "jabin.timestamp.mixin"
        _description = "JABIN Timestamp Mixin"

        create_date = fields.Datetime(
            string="Created On",
            readonly=True,
            help="Date and time when the record was created (UTC).",
        )
        write_date = fields.Datetime(
            string="Last Updated On",
            readonly=True,
            help="Date and time of the last write to the record (UTC).",
        )

else:  # pragma: no cover - fallback for non-Odoo test environments

    class TimestampMixin:  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""

        _name = "jabin.timestamp.mixin"
        _description = "JABIN Timestamp Mixin (stub)"
