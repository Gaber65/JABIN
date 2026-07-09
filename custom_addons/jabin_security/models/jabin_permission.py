# -*- coding: utf-8 -*-
"""Permission model for JABIN RBAC.

A :class:`JabinPermission` is an atomic, named capability in the system
(e.g. ``"users.create"``, ``"orders.refund"``). Permissions follow a
``<resource>.<action>`` naming convention for clarity and grouping.

Design
------
* ``code`` is the unique machine-readable identifier (e.g. ``"users.create"``).
* ``name`` is a human-readable label.
* ``resource`` and ``action`` are extracted from the code for filtering /
  grouping in the UI.
* Permissions are system-defined (``is_system=True``) and non-deletable by
  default. Business modules declare their permissions in their own data XML
  files and reference them by code.
* Permissions are assigned to users *through roles*, not directly (though the
  model allows direct assignment for edge cases).
"""

from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from jabin_core import JabinLogger

_logger = JabinLogger.get("security.permission")


class JabinPermission(models.Model):
    """Atomic capability in the JABIN RBAC system."""

    _name = "jabin.permission"
    _description = "JABIN Permission"
    _order = "resource, action"
    _rec_name = "code"

    code = fields.Char(
        string="Permission Code",
        required=True,
        index=True,
        help="Unique identifier in '<resource>.<action>' format "
             "(e.g. 'users.create').",
    )
    name = fields.Char(
        string="Display Name",
        required=True,
        help="Human-readable label.",
    )
    description = fields.Text(
        string="Description",
        help="What this permission allows.",
    )
    resource = fields.Char(
        string="Resource",
        index=True,
        help="The domain resource this permission applies to "
             "(extracted from the code).",
    )
    action = fields.Char(
        string="Action",
        index=True,
        help="The action this permission allows (extracted from the code).",
    )
    is_system = fields.Boolean(
        string="System Permission",
        default=True,
        help="System permissions are predefined and cannot be deleted.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relations
    # ------------------------------------------------------------------ #
    role_ids = fields.Many2many(
        comodel_name="jabin.role",
        relation="jabin_role_permission_rel",
        column1="permission_id",
        column2="role_id",
        string="Roles",
        help="Roles that grant this permission.",
    )

    # ------------------------------------------------------------------ #
    # Constraints
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        ("code_unique", "unique(code)", "A permission with this code already exists."),
    ]

    @api.constrains("code")
    def _check_code_format(self):
        """Permission codes must follow ``resource.action`` snake_case format."""
        import re
        for rec in self:
            if rec.code and not re.match(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$", rec.code):
                raise ValidationError(
                    f"Permission code '{rec.code}' must follow the "
                    f"'<resource>.<action>' convention "
                    f"(lowercase snake_case, single dot separator)."
                )

    # ------------------------------------------------------------------ #
    # ORM overrides
    # ------------------------------------------------------------------ #
    @api.model
    def create(self, vals_list):
        """Auto-extract resource / action from the code on creation."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            self._split_code(vals)
        return super().create(vals_list)

    def write(self, vals):
        """Auto-extract resource / action when the code changes."""
        if "code" in vals:
            self._split_code(vals)
        return super().write(vals)

    def unlink(self):
        """Prevent deletion of system permissions."""
        system = self.filtered("is_system")
        if system:
            raise ValidationError(
                f"Cannot delete system permissions: {', '.join(system.mapped('code'))}"
            )
        return super().unlink()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _split_code(vals: dict) -> None:
        """Extract ``resource`` and ``action`` from the ``code`` field."""
        code = vals.get("code")
        if not code or "." not in code:
            return
        parts = code.split(".", 1)
        vals.setdefault("resource", parts[0])
        vals.setdefault("action", parts[1])

    @api.model
    def find_by_code(self, code: str):
        """Return the permission matching ``code`` (or empty recordset)."""
        if not code:
            return self.env["jabin.permission"]
        return self.search([("code", "=", code)], limit=1)

    def to_public_dict(self) -> dict:
        """JSON-safe dict of the permission."""
        self.ensure_one()
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "resource": self.resource,
            "action": self.action,
            "description": self.description or None,
            "is_system": self.is_system,
        }
