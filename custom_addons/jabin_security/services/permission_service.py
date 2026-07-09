# -*- coding: utf-8 -*-
"""Permission service for the JABIN RBAC system.

Manages the role / permission catalog: creating, listing, and assigning roles
to users. This is the administrative service used by the (future) admin UI and
by seed-data scripts.

Responsibilities
----------------
* CRUD for roles and permissions.
* Assigning / revoking roles on users.
* Resolving the full permission set for a given user (used by
  ``AuthorizationService``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from odoo import api, fields, models
from odoo.exceptions import MissingError, ValidationError

from jabin_core import JabinLogger

_logger = JabinLogger.get("security.permission_service")


class PermissionService(models.AbstractModel):
    """Administrative service for the RBAC catalog."""

    _name = "jabin.permission.service"
    _description = "JABIN Permission Service"

    # ------------------------------------------------------------------ #
    # Role management
    # ------------------------------------------------------------------ #
    @api.model
    def create_role(
        self,
        code: str,
        name: str,
        description: str = "",
        permission_codes: Optional[List[str]] = None,
        is_system: bool = False,
    ) -> Dict[str, Any]:
        """Create a new role and optionally attach permissions."""
        if not code or not name:
            raise ValidationError("Role 'code' and 'name' are required.")
        existing = self.env["jabin.role"].find_by_code(code)
        if existing:
            raise ValidationError(f"Role '{code}' already exists.")

        vals = {
            "code": code,
            "name": name,
            "description": description,
            "is_system": is_system,
        }
        role = self.env["jabin.role"].create(vals)

        if permission_codes:
            perms = self.env["jabin.permission"].search(
                [("code", "in", permission_codes)]
            )
            role.write({"permission_ids": [(6, 0, perms.ids)]})

        _logger.audit(
            "Role created: code=%s permissions=%s", code, permission_codes or [],
            extra={"role_id": role.id, "action": "create_role"},
        )
        return self._role_to_dict(role)

    @api.model
    def get_role(self, role_id: int) -> Dict[str, Any]:
        """Return a role by ID."""
        role = self.env["jabin.role"].browse(role_id)
        if not role.exists():
            raise MissingError(f"Role {role_id} not found.")
        return self._role_to_dict(role)

    @api.model
    def list_roles(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List all roles."""
        domain = [] if include_inactive else [("active", "=", True)]
        roles = self.env["jabin.role"].search(domain, order="sequence, code")
        return [self._role_to_dict(r) for r in roles]

    @api.model
    def update_role(
        self,
        role_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update a role's metadata and/or permissions."""
        role = self.env["jabin.role"].browse(role_id)
        if not role.exists():
            raise MissingError(f"Role {role_id} not found.")

        vals: Dict[str, Any] = {}
        if name is not None:
            vals["name"] = name
        if description is not None:
            vals["description"] = description
        if permission_codes is not None:
            perms = self.env["jabin.permission"].search(
                [("code", "in", permission_codes)]
            )
            vals["permission_ids"] = [(6, 0, perms.ids)]

        if vals:
            role.write(vals)
            _logger.audit(
                "Role updated: id=%s fields=%s", role_id, list(vals.keys()),
                extra={"role_id": role_id, "action": "update_role"},
            )
        return self._role_to_dict(role)

    # ------------------------------------------------------------------ #
    # Permission catalog
    # ------------------------------------------------------------------ #
    @api.model
    def list_permissions(self, resource: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all permissions, optionally filtered by resource."""
        domain = []
        if resource:
            domain.append(("resource", "=", resource))
        perms = self.env["jabin.permission"].search(domain, order="resource, action")
        return [p.to_public_dict() for p in perms]

    # ------------------------------------------------------------------ #
    # Role assignment
    # ------------------------------------------------------------------ #
    @api.model
    def assign_role(self, user_id: int, role_code: str) -> Dict[str, Any]:
        """Assign a role to a user."""
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        role = self.env["jabin.role"].find_by_code(role_code)
        if not role:
            raise MissingError(f"Role '{role_code}' not found.")
        user.write({"x_jabin_role_ids": [(4, role.id)]})
        _logger.audit(
            "Role assigned: user=%s role=%s", user_id, role_code,
            extra={"user_id": user_id, "role_code": role_code, "action": "assign_role"},
        )
        return {"user_id": user_id, "role_code": role_code, "assigned": True}

    @api.model
    def revoke_role(self, user_id: int, role_code: str) -> Dict[str, Any]:
        """Revoke a role from a user."""
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        role = self.env["jabin.role"].find_by_code(role_code)
        if not role:
            raise MissingError(f"Role '{role_code}' not found.")
        user.write({"x_jabin_role_ids": [(3, role.id)]})
        _logger.audit(
            "Role revoked: user=%s role=%s", user_id, role_code,
            extra={"user_id": user_id, "role_code": role_code, "action": "revoke_role"},
        )
        return {"user_id": user_id, "role_code": role_code, "assigned": False}

    @api.model
    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """List the roles assigned to a user."""
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        return [self._role_to_dict(r) for r in user.x_jabin_role_ids]

    # ------------------------------------------------------------------ #
    # Resolution (used by AuthorizationService)
    # ------------------------------------------------------------------ #
    @api.model
    def resolve_permissions(self, user_id: int) -> Set[str]:
        """Return the full set of permission codes for ``user_id``.

        This delegates to ``res.users.get_permission_codes()`` which
        aggregates all permissions from all of the user's roles.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            return set()
        return user.get_permission_codes()

    @api.model
    def resolve_roles(self, user_id: int) -> List[str]:
        """Return the list of role codes for ``user_id``."""
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            return []
        return user.get_role_codes()

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    @staticmethod
    def _role_to_dict(role) -> Dict[str, Any]:
        return {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description or None,
            "is_system": role.is_system,
            "active": role.active,
            "permissions": [p.code for p in role.permission_ids],
            "user_count": len(role.user_ids),
        }


# Late import for type hints (avoid circular at module load).
from typing import Any  # noqa: E402
