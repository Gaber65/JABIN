# -*- coding: utf-8 -*-
"""User management REST controller for the JABIN platform.

Exposes CRUD endpoints under ``/api/v1/users``. The controller is a **thin
HTTP adapter**: it parses the request, delegates to
:class:`~jabin_users.services.user_service.UserService`, and serialises the
result through the Sprint 1 unified envelope. No business logic lives here.

Endpoints
---------
* ``GET    /api/v1/users``          – paginated list (filters: user_type, status, search)
* ``POST   /api/v1/users``          – create a user
* ``GET    /api/v1/users/{id}``     – get a single user
* ``PUT    /api/v1/users/{id}``     – update a user
* ``DELETE /api/v1/users/{id}``     – archive (soft-delete) a user
* ``POST   /api/v1/users/{id}/restore``  – restore an archived user
* ``PATCH  /api/v1/users/{id}/status``   – change account status

Auth
----
Sprint 2 uses ``auth="none"`` with a placeholder for the JWT decorator that
will be wired in ``jabin_security``. The controllers are written so that
adding the decorator (once available) requires only decorating each route,
without changing the handler body.
"""

from __future__ import annotations

import math
from typing import Any, Dict

try:
    from odoo import http  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover
    _ODOO = False
    http = None  # type: ignore

from jabin_core import ResponseBuilder, ValidationHelper

from jabin_api.controllers.base import BaseApiController


if _ODOO:

    class UserController(BaseApiController):
        """REST controller for JABIN user management (``/api/v1/users``)."""

        # ------------------------------------------------------------------ #
        # List users
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users",
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        def list_users(self, **kwargs: Any):
            """Paginated list of users with optional filters.

            Query params: ``page``, ``per_page``, ``user_type``, ``status``,
            ``search``.
            """
            with self.handle() as ctx:
                page = ValidationHelper.to_int(kwargs.get("page"), 1) or 1
                per_page = ValidationHelper.to_int(kwargs.get("per_page"), 20) or 20
                user_type = kwargs.get("user_type") or None
                status = kwargs.get("status") or None
                search = kwargs.get("search") or None

                svc = http.request.env["jabin.user.service"]
                data, meta = svc.list_users(
                    page=page,
                    per_page=per_page,
                    user_type=user_type,
                    status=status,
                    search=search,
                )
                ctx.set_body(
                    ResponseBuilder.success(
                        data=data,
                        meta=meta,
                        message="Users retrieved successfully",
                    )
                )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Create user
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        def create_user(self, **kwargs: Any):
            """Create a new JABIN user."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                svc = http.request.env["jabin.user.service"]
                user_dict = svc.create_user(payload)
                ctx.set_body(
                    ResponseBuilder.created(
                        data=user_dict,
                        message="User created successfully",
                    )
                )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Get single user
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users/<int:user_id>",
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        def get_user(self, user_id: int, **kwargs: Any):
            """Return a single user by ID."""
            with self.handle() as ctx:
                svc = http.request.env["jabin.user.service"]
                user_dict = svc.get_user(user_id)
                ctx.set_body(
                    ResponseBuilder.success(
                        data=user_dict,
                        message="User retrieved successfully",
                    )
                )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Update user
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users/<int:user_id>",
            methods=["PUT"],
            type="http",
            auth="none",
            csrf=False,
        )
        def update_user(self, user_id: int, **kwargs: Any):
            """Update an existing user."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                svc = http.request.env["jabin.user.service"]
                user_dict = svc.update_user(user_id, payload)
                ctx.set_body(
                    ResponseBuilder.success(
                        data=user_dict,
                        message="User updated successfully",
                    )
                )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Archive user (soft delete)
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users/<int:user_id>",
            methods=["DELETE"],
            type="http",
            auth="none",
            csrf=False,
        )
        def delete_user(self, user_id: int, **kwargs: Any):
            """Archive (soft-delete) a user."""
            with self.handle() as ctx:
                svc = http.request.env["jabin.user.service"]
                result = svc.archive_user(user_id)
                ctx.set_body(
                    ResponseBuilder.success(
                        data=result,
                        message="User archived successfully",
                    )
                )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Restore user
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users/<int:user_id>/restore",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        def restore_user(self, user_id: int, **kwargs: Any):
            """Restore an archived user."""
            with self.handle() as ctx:
                svc = http.request.env["jabin.user.service"]
                result = svc.restore_user(user_id)
                ctx.set_body(
                    ResponseBuilder.success(
                        data=result,
                        message="User restored successfully",
                    )
                )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Change status
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/users/<int:user_id>/status",
            methods=["PATCH"],
            type="http",
            auth="none",
            csrf=False,
        )
        def change_status(self, user_id: int, **kwargs: Any):
            """Change the account lifecycle status."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                status = payload.get("status")
                if not status:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "status", "message": "status is required."}]
                        )
                    )
                else:
                    svc = http.request.env["jabin.user.service"]
                    result = svc.set_status(user_id, status)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="User status updated successfully",
                        )
                    )
            return ctx.response

else:  # pragma: no cover

    class UserController(BaseApiController):  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""
