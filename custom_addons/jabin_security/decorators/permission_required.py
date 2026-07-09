# -*- coding: utf-8 -*-
"""Permission decorator for JABIN REST controllers.

The :func:`permission_required` decorator checks that the authenticated user
holds a specific permission (or set of permissions) before allowing the
handler to execute. It relies on the :class:`SecurityContext` that was built
and stored by :func:`~jabin_security.decorators.auth_required.auth_required`.

Usage
-----
Single permission::

    @http.route("/api/v1/users", methods=["POST"], ...)
    @auth_required
    @permission_required("users.create")
    def create_user(self, **kwargs):
        ...

Any-of (user needs at least one)::

    @permission_required(any_of=["users.read", "users.export"])

All-of (user needs every one)::

    @permission_required(all_of=["orders.refund", "orders.view"])

Design
------
* The decorator reads the context from ``SecurityContext.get()``. If no
  context is present (the handler was not wrapped with ``auth_required``),
  it returns a ``401``.
* Authorization is delegated to ``AuthorizationService.authorize()`` which
  also checks the account is still active.
* On failure, a ``403`` response with the unified envelope is returned; the
  unauthorized attempt is written to the audit log.
* ``admin`` users short-circuit — they always pass (handled inside
  :class:`SecurityContext`).
* The decorator can be stacked: applying multiple ``@permission_required``
  decorators means **all** of them must pass.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, List, Optional

from jabin_core import ResponseBuilder
from jabin_security.utils.security_context import SecurityContext


def permission_required(
    permission: Optional[str] = None,
    *,
    any_of: Optional[List[str]] = None,
    all_of: Optional[List[str]] = None,
) -> Callable:
    """Decorator factory that enforces RBAC permission checks.

    Parameters
    ----------
    permission:
        A single permission code the user must hold.
    any_of:
        The user must hold at least one of these permission codes.
    all_of:
        The user must hold all of these permission codes.

    At most one of the three should be supplied; if several are given, all
    supplied checks must pass.
    """
    # Normalise: merge ``permission`` into ``all_of`` for simplicity.
    required_all: List[str] = list(all_of or [])
    if permission:
        required_all.append(permission)
    required_any: List[str] = list(any_of or [])

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any):
            try:
                from odoo.http import request  # type: ignore
            except Exception:  # pragma: no cover
                return func(self, *args, **kwargs)

            ctx = SecurityContext.get()

            # No context → the route was not protected by auth_required.
            if not ctx.is_authenticated:
                envelope = ResponseBuilder.unauthorized(
                    message="Authentication required before permission check.",
                )
                return self._build_response(envelope, status=401)

            # Delegate the decision to the authorization service.
            authz_svc = request.env["jabin.authorization.service"]
            allowed = authz_svc.authorize(
                ctx,
                any_of=required_any or None,
                all_of=required_all or None,
                require_active_account=True,
            )

            if not allowed:
                # Audit the blocked attempt.
                try:
                    request.env["jabin.audit.service"].log_unauthorized(
                        user_id=ctx.user_id,
                        action="authz.permission_denied",
                        permission=permission,
                        any_of=required_any,
                        all_of=required_all,
                    )
                except Exception:
                    pass

                envelope = ResponseBuilder.forbidden(
                    message="You do not have permission to perform this action.",
                )
                return self._build_response(envelope, status=403)

            return func(self, *args, **kwargs)

        wrapper._jabin_permission = {  # type: ignore[attr-defined]
            "permission": permission,
            "any_of": required_any,
            "all_of": required_all,
        }
        return wrapper

    return decorator
