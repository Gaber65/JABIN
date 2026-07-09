# -*- coding: utf-8 -*-
"""Authorization service for the JABIN RBAC system.

The :class:`AuthorizationService` is the single entry point for building
:class:`~jabin_security.utils.security_context.SecurityContext` objects and for
making authorization decisions. It sits between the low-level models
(``jabin.role``, ``jabin.permission``) and the high-level HTTP decorators
(``auth_required``, ``permission_required``).

Responsibilities
----------------
* **Build a SecurityContext** for a given user by resolving their roles and
  permissions from the database.
* **Validate a SecurityContext** against a permission requirement (single,
  any-of, all-of).
* **Check account status** – a user whose account is suspended or archived is
  not authorized even if they hold a valid token and the right roles.

Design
------
* The service is an :class:`odoo.models.AbstractModel` so that it inherits the
  Odoo environment (``self.env``) and can query the ORM without manual
  environment management.
* All methods are ``@api.model`` (no record-set state) because authorization
  is stateless – each call is independent.
* The service never raises on a *negative* authorization decision; it returns
  ``False`` / ``None`` so that decorators can map the result to a ``403``
  without a try/except. It *does* raise on programming errors (bad input,
  missing user).
* Admin users (``user_type == "admin"``) short-circuit: they are always
  authorized. This mirrors the short-circuit in
  :meth:`SecurityContext.has_permission`.
"""

from __future__ import annotations

from typing import List, Optional, Set

from odoo import api, models
from odoo.exceptions import MissingError

from jabin_core import JabinLogger
from jabin_security.utils.security_context import SecurityContext

_logger = JabinLogger.get("security.authorization_service")


class AuthorizationService(models.AbstractModel):
    """Builds security contexts and makes authorization decisions."""

    _name = "jabin.authorization.service"
    _description = "JABIN Authorization Service"

    # ------------------------------------------------------------------ #
    # Context construction
    # ------------------------------------------------------------------ #
    @api.model
    def build_context(
        self,
        user_id: int,
        token_id: Optional[str] = None,
    ) -> SecurityContext:
        """Resolve a user's identity, roles, and permissions into a context.

        Parameters
        ----------
        user_id:
            The ``res.users`` ID of the authenticated user.
        token_id:
            The ``jti`` of the access token, if available (carried through
            for audit logging).

        Raises
        ------
        MissingError:
            If the user does not exist.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")

        roles: List[str] = list(user.get_role_codes())
        permissions: Set[str] = set(user.get_permission_codes())

        # Read the JABIN-specific profile fields added by jabin_users.
        user_type = getattr(user, "x_user_type", None) or None
        email = user.login or None

        ctx = SecurityContext(
            user_id=user_id,
            user_type=user_type,
            email=email,
            roles=roles,
            permissions=permissions,
            token_id=token_id,
        )
        _logger.debug(
            "Built security context for user %s: roles=%s perms=%d",
            user_id, roles, len(permissions),
        )
        return ctx

    # ------------------------------------------------------------------ #
    # Account-status gate
    # ------------------------------------------------------------------ #
    @api.model
    def is_account_active(self, user_id: int) -> bool:
        """Return ``True`` if the user's account is active and usable.

        A user is considered active when:
        * The record exists.
        * ``x_is_active_account`` is ``True`` (the JABIN business flag, not
          Odoo's native ``active`` which is tied to archiving).
        * ``x_status`` is one of the active lifecycle states
          (``"active"``, ``"pending"``). Suspended or banned users are
          rejected.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            return False

        if not getattr(user, "x_is_active_account", True):
            return False

        status = getattr(user, "x_status", None)
        # Active lifecycle states.  ``pending`` is allowed because a pending
        # user may still authenticate (e.g. to complete onboarding) but a
        # ``suspended`` or ``banned`` user must not.
        if status and status not in ("active", "pending"):
            return False

        return True

    # ------------------------------------------------------------------ #
    # Authorization decisions
    # ------------------------------------------------------------------ #
    @api.model
    def check_permission(
        self,
        ctx: SecurityContext,
        permission_code: str,
    ) -> bool:
        """Return ``True`` if ``ctx`` grants ``permission_code``.

        Admins always pass. Anonymous contexts always fail.
        """
        if not ctx or not ctx.is_authenticated:
            return False
        return ctx.has_permission(permission_code)

    @api.model
    def check_any_permission(
        self,
        ctx: SecurityContext,
        permission_codes: List[str],
    ) -> bool:
        """Return ``True`` if ``ctx`` grants at least one of the codes."""
        if not ctx or not ctx.is_authenticated:
            return False
        return ctx.has_any_permission(permission_codes)

    @api.model
    def check_all_permissions(
        self,
        ctx: SecurityContext,
        permission_codes: List[str],
    ) -> bool:
        """Return ``True`` if ``ctx`` grants every one of the codes."""
        if not ctx or not ctx.is_authenticated:
            return False
        if not permission_codes:
            return True
        return ctx.has_all_permissions(permission_codes)

    @api.model
    def check_role(self, ctx: SecurityContext, role_code: str) -> bool:
        """Return ``True`` if ``ctx`` includes ``role_code``.

        Admins always pass (they implicitly hold every role).
        """
        if not ctx or not ctx.is_authenticated:
            return False
        if ctx.is_admin:
            return True
        return ctx.has_role(role_code)

    # ------------------------------------------------------------------ #
    # Full guard: status + permission
    # ------------------------------------------------------------------ #
    @api.model
    def authorize(
        self,
        ctx: SecurityContext,
        permission_code: Optional[str] = None,
        any_of: Optional[List[str]] = None,
        all_of: Optional[List[str]] = None,
        require_active_account: bool = True,
    ) -> bool:
        """Combined authorization gate used by the ``permission_required``
        decorator.

        Parameters
        ----------
        ctx:
            The request's security context (built by ``auth_required``).
        permission_code:
            A single required permission.
        any_of:
            The user must hold *at least one* of these permissions.
        all_of:
            The user must hold *all* of these permissions.
        require_active_account:
            When ``True`` (default), the user's account must be in an active
            lifecycle state.

        At most one of ``permission_code`` / ``any_of`` / ``all_of`` should be
        supplied; if several are given, *all* supplied checks must pass.
        """
        if not ctx or not ctx.is_authenticated:
            return False

        if require_active_account and ctx.user_id is not None:
            if not self.is_account_active(ctx.user_id):
                _logger.audit(
                    "Authorization denied – inactive account: user=%s",
                    ctx.user_id,
                    extra={"user_id": ctx.user_id, "action": "authz_denied_inactive"},
                )
                return False

        if permission_code and not self.check_permission(ctx, permission_code):
            return False
        if any_of and not self.check_any_permission(ctx, any_of):
            return False
        if all_of and not self.check_all_permissions(ctx, all_of):
            return False

        return True
