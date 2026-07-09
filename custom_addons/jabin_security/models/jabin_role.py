# -*- coding: utf-8 -*-
"""Role model for JABIN RBAC.

A :class:`JabinRole` groups a set of permissions into a named bundle that can
be assigned to users. Roles are the primary mechanism for granting access in
JABIN; individual permissions are rarely assigned directly.

Design
------
* Roles use a unique ``code`` (e.g. ``"order_manager"``) for programmatic
  reference and a human-readable ``name`` for the UI.
* A role is linked to many permissions via ``jabin.role.permission`` (a
  many2many through the standard Odoo relation table).
* Roles can be system-defined (``is_system=True``, non-deletable) or
  user-defined.
* The ``user_ids`` field tracks which users have this role (many2many to
  ``res.users`` via the ``x_jabin_role_ids`` field added by
  :mod:`res_users_security`).
"""

from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from jabin_core import JabinLogger

_logger = JabinLogger.get("security.role")


class JabinRole(models.Model):
    """Named bundle of permissions assignable to users."""

    _name = "jabin.role"
    _description = "JABIN Role"
    _order = "sequence, code"
    _rec_name = "code"

    code = fields.Char(
        string="Role Code",
        required=True,
        index=True,
        help="Unique machine-readable role identifier (e.g. 'order_manager').",
    )
    name = fields.Char(
        string="Display Name",
        required=True,
        help="Human-readable role name.",
    )
    description = fields.Text(
        string="Description",
        help="What this role grants and when it should be assigned.",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Display order in lists.",
    )
    is_system = fields.Boolean(
        string="System Role",
        default=False,
        help="System roles are predefined and cannot be deleted.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relations
    # ------------------------------------------------------------------ #
    permission_ids = fields.Many2many(
        comodel_name="jabin.permission",
        relation="jabin_role_permission_rel",
        column1="role_id",
        column2="permission_id",
        string="Permissions",
        help="Permissions granted by this role.",
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="jabin_role_user_rel",
        column1="role_id",
        column2="user_id",
        string="Users",
        help="Users assigned to this role.",
    )

    # ------------------------------------------------------------------ #
    # Constraints
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        ("code_unique", "unique(code)", "A role with this code already exists."),
    ]

    @api.constrains("code")
    def _check_code_format(self):
        """Role codes must be lowercase snake_case (no spaces / specials)."""
        import re
        for rec in self:
            if rec.code and not re.match(r"^[a-z][a-z0-9_]*$", rec.code):
                raise ValidationError(
                    f"Role code '{rec.code}' must be lowercase snake_case "
                    f"(letters, digits, underscores; starting with a letter)."
                )

    # ------------------------------------------------------------------ #
    # ORM overrides
    # ------------------------------------------------------------------ #
    def unlink(self):
        """Prevent deletion of system roles."""
        system = self.filtered("is_system")
        if system:
            raise ValidationError(
                f"Cannot delete system roles: {', '.join(system.mapped('code'))}"
            )
        return super().unlink()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @api.model
    def find_by_code(self, code: str):
        """Return the role matching ``code`` (or empty recordset)."""
        if not code:
            return self.env["jabin.role"]
        return self.search([("code", "=", code)], limit=1)

    def get_permission_codes(self) -> set:
        """Return the set of permission codes granted by this role(s)."""
        self.ensure_one() if len(self) == 1 else None  # support multi too
        perms = self.mapped("permission_ids.code")
        return set(perms)
