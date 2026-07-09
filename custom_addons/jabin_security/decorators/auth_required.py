# -*- coding: utf-8 -*-
"""Authentication decorator for JABIN REST controllers.

The :func:`auth_required` decorator extracts the JWT bearer token from the
``Authorization`` header, decodes and verifies it, resolves the user, builds a
:class:`~jabin_security.utils.security_context.SecurityContext`, and stores it
on the request so that downstream code (controllers, services, the
``permission_required`` decorator) can access it via
``SecurityContext.get()``.

Flow
----
1. Read the ``Authorization`` header; expect ``Bearer <token>``.
2. Decode and verify the token with
   :class:`~jabin_security.utils.jwt_utils.JWTUtils`.
3. Verify the token kind is ``"access"`` (refresh tokens must not be used for
   API calls).
4. Resolve the user via ``res.users`` and check the account is active.
5. Build a :class:`SecurityContext` via ``AuthorizationService`` and store it
   on the request.
6. Call the wrapped handler.

Failure modes
-------------
If any step fails the decorator **does not call** the handler. Instead it
returns a ready-made error response (``401`` for missing/invalid/expired
tokens, ``403`` for inactive accounts) using the unified envelope so the
client gets a consistent error shape.

Design
------
* The decorator is designed for Odoo ``type="http"`` controllers whose
  handlers return an :class:`odoo.http.Response`.
* It works with the ``self.handle()`` pattern from
  :class:`~jabin_api.controllers.base.BaseApiController` — the decorator wraps
  the *entire* handler, so if the handler uses ``self.handle()`` internally,
  the auth failure short-circuits before ``handle()`` is entered.
* ``optional=True`` makes the decorator build an anonymous context and proceed
  even when no token is present (useful for endpoints that behave differently
  for anonymous vs. authenticated users).
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from jabin_core import ResponseBuilder
from jabin_security.utils.jwt_utils import JWTError, JWTUtils
from jabin_security.utils.security_context import SecurityContext


def _extract_bearer_token(raw_header: str) -> str:
    """Extract the token from an ``Authorization`` header value.

    Returns an empty string when the header is missing or malformed.
    """
    if not raw_header:
        return ""
    parts = raw_header.split(None, 1)  # split on first whitespace
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def auth_required(func: Callable) -> Callable:
    """Decorator that enforces JWT authentication on a controller route.

    Usage::

        @http.route("/api/v1/users", methods=["GET"], type="http", auth="none", csrf=False)
        @auth_required
        def list_users(self, **kwargs):
            with self.handle() as ctx:
                ...

    The decorator must be applied **below** the ``@http.route`` decorator so
    that Odoo registers the route on the original function and the wrapper is
    invoked at call time.
    """
    return _build_auth_decorator(func, optional=False)


def auth_optional(func: Callable) -> Callable:
    """Like :func:`auth_required` but allows anonymous access.

    When no token is present, an anonymous :class:`SecurityContext` is stored
    and the handler is called normally. When a token *is* present, it must be
    valid (invalid tokens still produce a ``401``).
    """
    return _build_auth_decorator(func, optional=True)


def _build_auth_decorator(func: Callable, *, optional: bool) -> Callable:
    """Shared implementation for :func:`auth_required` and
    :func:`auth_optional`.
    """

    @functools.wraps(func)
    def wrapper(self, *args: Any, **kwargs: Any):
        # Import Odoo lazily so the module is importable in non-Odoo contexts.
        try:
            from odoo import http  # type: ignore
            from odoo.http import request  # type: ignore
        except Exception:  # pragma: no cover
            return func(self, *args, **kwargs)

        # --- 1. Extract the bearer token -------------------------------- #
        raw_header = ""
        try:
            httprequest = request.httprequest
            raw_header = httprequest.headers.get("Authorization", "")
        except Exception:
            raw_header = ""

        token = _extract_bearer_token(raw_header)

        # --- Optional mode: no token → anonymous context --------------- #
        if not token:
            if optional:
                SecurityContext.set(SecurityContext.anonymous())
                return func(self, *args, **kwargs)
            envelope = ResponseBuilder.unauthorized(
                message="Authentication required. Provide a Bearer token.",
                errors=[{"field": "Authorization", "message": "Missing Bearer token."}],
            )
            return self._build_response(envelope, status=401)

        # --- 2. Decode and verify the token ----------------------------- #
        try:
            claims = JWTUtils.decode_token(token)
        except JWTError as exc:
            envelope = ResponseBuilder.unauthorized(
                message=str(exc),
                errors=[{"field": "Authorization", "message": str(exc)}],
            )
            return self._build_response(envelope, status=401)

        # --- 3. Verify token kind --------------------------------------- #
        kind = JWTUtils.get_token_kind(claims)
        if kind != "access":
            envelope = ResponseBuilder.unauthorized(
                message="Invalid token type. An access token is required.",
                errors=[{"field": "Authorization", "message": "Not an access token."}],
            )
            return self._build_response(envelope, status=401)

        # --- 4. Resolve the user ---------------------------------------- #
        user_id = JWTUtils.get_user_id(claims)
        if user_id is None:
            envelope = ResponseBuilder.unauthorized(
                message="Token does not contain a valid user identifier.",
            )
            return self._build_response(envelope, status=401)

        user = request.env["res.users"].browse(user_id)
        if not user.exists():
            envelope = ResponseBuilder.unauthorized(
                message="Token references a non-existent user.",
            )
            return self._build_response(envelope, status=401)

        # --- 5. Check account status ------------------------------------ #
        authz_svc = request.env["jabin.authorization.service"]
        if not authz_svc.is_account_active(user_id):
            # Audit the blocked attempt.
            try:
                request.env["jabin.audit.service"].log(
                    action="auth.blocked_inactive",
                    severity="warning",
                    user_id=user_id,
                    summary="Access blocked – account not active",
                )
            except Exception:
                pass
            envelope = ResponseBuilder.forbidden(
                message="Account is suspended or inactive.",
            )
            return self._build_response(envelope, status=403)

        # --- 6. Build and store the security context -------------------- #
        token_id = JWTUtils.get_token_id(claims)
        ctx = authz_svc.build_context(user_id, token_id=token_id)
        SecurityContext.set(ctx)

        # --- 7. Call the handler ---------------------------------------- #
        return func(self, *args, **kwargs)

    # Tag the wrapper so introspection can tell it apart.
    wrapper._jabin_auth = True  # type: ignore[attr-defined]
    wrapper._jabin_auth_optional = optional  # type: ignore[attr-defined]
    return wrapper
