# -*- coding: utf-8 -*-
"""Request-scoped security context for the JABIN platform.

The :class:`SecurityContext` is a lightweight value object that carries the
authenticated user's identity and resolved permissions through the duration of
a single HTTP request. It is produced by the :func:`auth_required` decorator
and consumed by controllers, services, and the :func:`permission_required`
decorator.

Why a context object?
---------------------
* **Decoupling** – controllers do not need to know *how* the user was
  authenticated (JWT, session, API key). They just read the context.
* **Testability** – services can be unit-tested by constructing a
  ``SecurityContext`` directly, without spinning up a full auth flow.
* **Thread safety** – the context is stored per-request using Odoo's
  ``request.env.context`` so concurrent requests do not interfere.

Storage
-------
Inside an Odoo request, the context is stored in ``request.env.context`` under
the key ``jabin_security_ctx``. The classmethods :meth:`set` / :meth:`get`
handle the storage / retrieval so callers do not manipulate the Odoo context
directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Key under which the SecurityContext is stored in request.env.context.
_CTX_KEY: str = "jabin_security_ctx"


class SecurityContext:
    """Immutable snapshot of the authenticated user's identity and permissions.

    Attributes
    ----------
    user_id:
        The ``res.users`` ID of the authenticated user (``None`` when
        anonymous).
    user_type:
        The ``UserType`` value (e.g. ``"admin"``, ``"customer"``).
    email:
        The user's login email.
    roles:
        List of role codes the user has been granted.
    permissions:
        Set of permission codes the user holds (resolved from roles).
    token_id:
        The ``jti`` of the access token, if available (for audit logging).
    is_authenticated:
        ``True`` when a valid user is present.
    is_admin:
        ``True`` when ``user_type == "admin"`` (short-circuits permission
        checks).
    """

    __slots__ = (
        "user_id", "user_type", "email", "roles", "permissions",
        "token_id", "is_authenticated", "is_admin",
    )

    def __init__(
        self,
        *,
        user_id: Optional[int] = None,
        user_type: Optional[str] = None,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[set] = None,
        token_id: Optional[str] = None,
    ) -> None:
        self.user_id: Optional[int] = user_id
        self.user_type: Optional[str] = user_type
        self.email: Optional[str] = email
        self.roles: List[str] = list(roles) if roles else []
        self.permissions: set = set(permissions) if permissions else set()
        self.token_id: Optional[str] = token_id
        self.is_authenticated: bool = user_id is not None
        self.is_admin: bool = user_type == "admin"

    # ------------------------------------------------------------------ #
    # Permission checking
    # ------------------------------------------------------------------ #
    def has_permission(self, code: str) -> bool:
        """Return ``True`` if the user holds the given permission code.

        Admins always pass (short-circuit).
        """
        if self.is_admin:
            return True
        return code in self.permissions

    def has_any_permission(self, codes: List[str]) -> bool:
        """Return ``True`` if the user holds at least one of ``codes``."""
        if self.is_admin:
            return True
        return any(c in self.permissions for c in codes)

    def has_all_permissions(self, codes: List[str]) -> bool:
        """Return ``True`` if the user holds every one of ``codes``."""
        if self.is_admin:
            return True
        return all(c in self.permissions for c in codes)

    def has_role(self, role_code: str) -> bool:
        """Return ``True`` if the user has been granted ``role_code``."""
        return role_code in self.roles

    # ------------------------------------------------------------------ #
    # Serialization (for logging / debugging)
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe summary (never includes secrets)."""
        return {
            "user_id": self.user_id,
            "user_type": self.user_type,
            "email": self.email,
            "roles": list(self.roles),
            "permission_count": len(self.permissions),
            "token_id": self.token_id,
            "is_authenticated": self.is_authenticated,
            "is_admin": self.is_admin,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SecurityContext(user_id={self.user_id}, "
            f"user_type={self.user_type!r}, "
            f"is_admin={self.is_admin}, "
            f"roles={self.roles}, "
            f"permissions={len(self.permissions)})"
        )

    # ------------------------------------------------------------------ #
    # Odoo request-scoped storage helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def anonymous(cls) -> "SecurityContext":
        """Return a context representing an unauthenticated request."""
        return cls()

    @classmethod
    def set(cls, ctx: "SecurityContext") -> None:
        """Store ``ctx`` in the current Odoo request's environment context.

        Called by the ``auth_required`` decorator after successful
        authentication.
        """
        try:
            from odoo.http import request  # type: ignore
            request.env.context = {**request.env.context, _CTX_KEY: ctx}
        except Exception:
            pass  # Non-Odoo environment (unit tests) – context is passed directly.

    @classmethod
    def get(cls) -> "SecurityContext":
        """Retrieve the security context from the current Odoo request.

        Returns an anonymous context when none is set or when not inside a
        request (e.g. in a unit test or a cron job).
        """
        try:
            from odoo.http import request  # type: ignore
            ctx = request.env.context.get(_CTX_KEY)
            if ctx is not None:
                return ctx
        except Exception:
            pass
        return cls.anonymous()
