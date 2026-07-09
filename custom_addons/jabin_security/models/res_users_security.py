# -*- coding: utf-8 -*-
"""Security extension of ``res.users`` for JABIN RBAC.

Adds a many2many relationship from ``res.users`` to ``jabin.role`` so that
roles can be assigned to users. This follows the same extend-don't-replace
pattern as the ``jabin_users`` module.

Fields added
------------
* ``x_jabin_role_ids`` – many2many to ``jabin.role``; the roles granted to
  the user.

Why ``x_`` prefix?
-------------------
Consistent with the ``jabin_users`` extension; keeps JABIN custom fields
visually distinct from Odoo-native ``res.users`` fields.
"""

from __future__ import annotations

from odoo import fields, models

from jabin_core import JabinLogger

_logger = JabinLogger.get("security.res_users")


class JabinUserSecurity(models.Model):
    """Extend ``res.users`` with JABIN role assignments."""

    _inherit = "res.users"
    _description = "JABIN User Security Extension"

    x_jabin_role_ids = fields.Many2many(
        comodel_name="jabin.role",
        relation="jabin_role_user_rel",
        column1="user_id",
        column2="role_id",
        string="JABIN Roles",
        help="RBAC roles assigned to this user.",
    )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def get_role_codes(self) -> list:
        """Return the list of role codes assigned to the user."""
        self.ensure_one()
        return self.x_jabin_role_ids.mapped("code")

    def get_permission_codes(self) -> set:
        """Return the set of permission codes resolved from the user's roles.

        This is the primary method used by ``AuthorizationService`` to build
        the :class:`SecurityContext` permission set.
        """
        self.ensure_one()
        if not self.x_jabin_role_ids:
            return set()
        # Collect all permission codes from all roles.
        perms = self.x_jabin_role_ids.mapped("permission_ids.code")
        return set(perms)
