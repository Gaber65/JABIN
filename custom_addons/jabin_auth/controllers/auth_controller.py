# -*- coding: utf-8 -*-
"""Authentication REST controller for the JABIN platform.

Exposes the auth endpoints under ``/api/v1/auth/*``. The controller is a
**thin HTTP adapter**: it parses the request, delegates to
:class:`~jabin_auth.services.auth_service.AuthService`, and serialises the
result through the Sprint 1 unified envelope. No business logic lives here.

Endpoints
---------
* ``POST   /api/v1/auth/login``     – authenticate with email + password.
* ``POST   /api/v1/auth/logout``    – revoke the current refresh token.
* ``POST   /api/v1/auth/refresh``   – exchange a refresh token for a new pair.
* ``GET    /api/v1/auth/verify``    – verify the current access token.
* ``GET    /api/v1/auth/profile``   – get the authenticated user's profile.
* ``PUT    /api/v1/auth/profile``   – update the authenticated user's profile.
* ``POST   /api/v1/auth/change-password`` – change password (self-service).

Auth model
----------
* ``login``, ``refresh``, and ``verify`` use ``auth="none"`` (they are the
  auth entry points).
* ``logout``, ``profile`` (GET/PUT), and ``change-password`` are protected
  by the ``@auth_required`` decorator from ``jabin_security``, which builds
  the :class:`SecurityContext` and stores it on the request.
"""

from __future__ import annotations

from typing import Any

try:
    from odoo import http  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover
    _ODOO = False
    http = None  # type: ignore

from jabin_core import ResponseBuilder
from jabin_security import auth_required
from jabin_security.utils.security_context import SecurityContext
from jabin_api.controllers.base import BaseApiController


if _ODOO:

    class AuthController(BaseApiController):
        """REST controller for JABIN authentication (``/api/v1/auth/*``)."""

        # ================================================================== #
        # Login
        # ================================================================== #
        @http.route(
            "/api/v1/auth/login",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        def login(self, **kwargs: Any):
            """Authenticate a user and return tokens + profile."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                login_value = payload.get("login") or payload.get("email")
                password = payload.get("password")

                if not login_value or not password:
                    ctx.set_body(
                        ResponseBuilder.validation_error([
                            {"field": "login", "message": "login (email or phone) is required."}
                            if not login_value else
                            {"field": "password", "message": "password is required."},
                        ]),
                        status=400,
                    )
                else:
                    svc = http.request.env["jabin.auth.service"]
                    result = svc.login(login_value, password)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Login successful",
                        )
                    )
            return ctx.response

        # ================================================================== #
        # Logout
        # ================================================================== #
        @http.route(
            "/api/v1/auth/logout",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        @auth_required
        def logout(self, **kwargs: Any):
            """Revoke the current refresh token (logout)."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                refresh_token = payload.get("refresh_token")
                if not refresh_token:
                    ctx.set_body(
                        ResponseBuilder.validation_error([
                            {"field": "refresh_token", "message": "refresh_token is required."},
                        ]),
                        status=400,
                    )
                else:
                    sec_ctx = SecurityContext.get()
                    svc = http.request.env["jabin.auth.service"]
                    result = svc.logout(refresh_token, user_id=sec_ctx.user_id)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Logout successful",
                        )
                    )
            return ctx.response

        # ================================================================== #
        # Refresh
        # ================================================================== #
        @http.route(
            "/api/v1/auth/refresh",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        def refresh(self, **kwargs: Any):
            """Exchange a refresh token for a new access + refresh pair."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                refresh_token = payload.get("refresh_token")
                if not refresh_token:
                    ctx.set_body(
                        ResponseBuilder.validation_error([
                            {"field": "refresh_token", "message": "refresh_token is required."},
                        ]),
                        status=400,
                    )
                else:
                    svc = http.request.env["jabin.auth.service"]
                    result = svc.refresh(refresh_token)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Token refreshed successfully",
                        )
                    )
            return ctx.response

        # ================================================================== #
        # Verify
        # ================================================================== #
        @http.route(
            "/api/v1/auth/verify",
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        def verify(self, **kwargs: Any):
            """Verify the current access token (from the Authorization header)."""
            with self.handle() as ctx:
                # Extract the bearer token from the header.
                raw_header = ""
                try:
                    raw_header = http.request.httprequest.headers.get("Authorization", "")
                except Exception:
                    pass
                token = ""
                if raw_header:
                    parts = raw_header.split(None, 1)
                    if len(parts) == 2 and parts[0].lower() == "bearer":
                        token = parts[1].strip()

                if not token:
                    ctx.set_body(
                        ResponseBuilder.unauthorized(
                            message="Access token required in Authorization header.",
                        ),
                        status=401,
                    )
                else:
                    svc = http.request.env["jabin.auth.service"]
                    result = svc.verify(token)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Token is valid",
                        )
                    )
            return ctx.response

        # ================================================================== #
        # Profile (GET)
        # ================================================================== #
        @http.route(
            "/api/v1/auth/profile",
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        @auth_required
        def get_profile(self, **kwargs: Any):
            """Return the authenticated user's profile."""
            with self.handle() as ctx:
                sec_ctx = SecurityContext.get()
                svc = http.request.env["jabin.auth.service"]
                profile = svc.get_profile(sec_ctx.user_id)
                ctx.set_body(
                    ResponseBuilder.success(
                        data=profile,
                        message="Profile retrieved successfully",
                    )
                )
            return ctx.response

        # ================================================================== #
        # Profile (PUT)
        # ================================================================== #
        @http.route(
            "/api/v1/auth/profile",
            methods=["PUT"],
            type="http",
            auth="none",
            csrf=False,
        )
        @auth_required
        def update_profile(self, **kwargs: Any):
            """Update the authenticated user's own profile."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                sec_ctx = SecurityContext.get()
                svc = http.request.env["jabin.auth.service"]
                profile = svc.update_profile(sec_ctx.user_id, payload)
                ctx.set_body(
                    ResponseBuilder.success(
                        data=profile,
                        message="Profile updated successfully",
                    )
                )
            return ctx.response

        # ================================================================== #
        # Change password (self-service)
        # ================================================================== #
        @http.route(
            "/api/v1/auth/change-password",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        @auth_required
        def change_password(self, **kwargs: Any):
            """Change the authenticated user's password (requires current password)."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                current = payload.get("current_password")
                new = payload.get("new_password")

                if not current or not new:
                    ctx.set_body(
                        ResponseBuilder.validation_error([
                            {"field": "current_password", "message": "current_password is required."}
                            if not current else
                            {"field": "new_password", "message": "new_password is required."},
                        ]),
                        status=400,
                    )
                else:
                    sec_ctx = SecurityContext.get()
                    svc = http.request.env["jabin.auth.service"]
                    result = svc.change_password(sec_ctx.user_id, current, new)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Password changed successfully",
                        )
                    )
            return ctx.response

else:  # pragma: no cover

    class AuthController(BaseApiController):  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""
