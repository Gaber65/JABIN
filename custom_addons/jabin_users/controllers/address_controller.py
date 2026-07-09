# -*- coding: utf-8 -*-
"""Address management REST controller for the JABIN platform.

Exposes CRUD endpoints under ``/api/v1/addresses``. Like the user controller,
this is a thin HTTP adapter that delegates to
:class:`~jabin_users.services.address_service.AddressService`.

Endpoints
---------
* ``GET    /api/v1/addresses?user_id=<id>``         – list addresses for a user
* ``POST   /api/v1/addresses``                      – create an address
* ``GET    /api/v1/addresses/<int:id>?user_id=<id>`` – get a single address
* ``PUT    /api/v1/addresses/<int:id>``              – update an address
* ``DELETE /api/v1/addresses/<int:id>``              – delete an address
* ``POST   /api/v1/addresses/<int:id>/default``      – set as default

Auth
----
All endpoints require a ``user_id`` query/body parameter identifying the
owning user. In Sprint 2 this is passed explicitly; once the JWT decorator
from ``jabin_security`` is available, the user_id will be resolved from the
token and this parameter will become optional / overridden.
"""

from __future__ import annotations

from typing import Any

try:
    from odoo import http  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover
    _ODOO = False
    http = None  # type: ignore

from jabin_core import ResponseBuilder, ValidationHelper

from jabin_api.controllers.base import BaseApiController


if _ODOO:

    class AddressController(BaseApiController):
        """REST controller for JABIN user addresses (``/api/v1/addresses``)."""

        # ------------------------------------------------------------------ #
        # List addresses
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/addresses",
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        def list_addresses(self, **kwargs: Any):
            """List addresses for a user (paginated).

            Query params: ``user_id`` (required), ``page``, ``per_page``.
            """
            with self.handle() as ctx:
                user_id = ValidationHelper.to_int(kwargs.get("user_id"), None)
                if not user_id:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "user_id", "message": "user_id is required."}]
                        )
                    )
                else:
                    page = ValidationHelper.to_int(kwargs.get("page"), 1) or 1
                    per_page = ValidationHelper.to_int(kwargs.get("per_page"), 20) or 20
                    svc = http.request.env["jabin.address.service"]
                    data, meta = svc.list_addresses(
                        user_id=user_id, page=page, per_page=per_page
                    )
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=data,
                            meta=meta,
                            message="Addresses retrieved successfully",
                        )
                    )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Create address
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/addresses",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        def create_address(self, **kwargs: Any):
            """Create a new address for a user."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                user_id = ValidationHelper.to_int(payload.get("user_id"), None)
                if not user_id:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "user_id", "message": "user_id is required."}]
                        )
                    )
                else:
                    svc = http.request.env["jabin.address.service"]
                    addr_dict = svc.create_address(user_id, payload)
                    ctx.set_body(
                        ResponseBuilder.created(
                            data=addr_dict,
                            message="Address created successfully",
                        )
                    )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Get single address
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/addresses/<int:address_id>",
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        def get_address(self, address_id: int, **kwargs: Any):
            """Return a single address by ID (requires ``user_id``)."""
            with self.handle() as ctx:
                user_id = ValidationHelper.to_int(kwargs.get("user_id"), None)
                if not user_id:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "user_id", "message": "user_id is required."}]
                        )
                    )
                else:
                    svc = http.request.env["jabin.address.service"]
                    addr_dict = svc.get_address(address_id, user_id)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=addr_dict,
                            message="Address retrieved successfully",
                        )
                    )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Update address
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/addresses/<int:address_id>",
            methods=["PUT"],
            type="http",
            auth="none",
            csrf=False,
        )
        def update_address(self, address_id: int, **kwargs: Any):
            """Update an existing address."""
            with self.handle() as ctx:
                payload = self.parse_json_body()
                user_id = ValidationHelper.to_int(payload.pop("user_id", None), None)
                if not user_id:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "user_id", "message": "user_id is required."}]
                        )
                    )
                else:
                    svc = http.request.env["jabin.address.service"]
                    addr_dict = svc.update_address(address_id, user_id, payload)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=addr_dict,
                            message="Address updated successfully",
                        )
                    )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Delete address
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/addresses/<int:address_id>",
            methods=["DELETE"],
            type="http",
            auth="none",
            csrf=False,
        )
        def delete_address(self, address_id: int, **kwargs: Any):
            """Delete an address."""
            with self.handle() as ctx:
                user_id = ValidationHelper.to_int(kwargs.get("user_id"), None)
                if not user_id:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "user_id", "message": "user_id is required."}]
                        )
                    )
                else:
                    svc = http.request.env["jabin.address.service"]
                    result = svc.delete_address(address_id, user_id)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Address deleted successfully",
                        )
                    )
            return ctx.response

        # ------------------------------------------------------------------ #
        # Set default address
        # ------------------------------------------------------------------ #
        @http.route(
            "/api/v1/addresses/<int:address_id>/default",
            methods=["POST"],
            type="http",
            auth="none",
            csrf=False,
        )
        def set_default_address(self, address_id: int, **kwargs: Any):
            """Mark an address as the user's default."""
            with self.handle() as ctx:
                user_id = ValidationHelper.to_int(kwargs.get("user_id"), None)
                if not user_id:
                    ctx.set_body(
                        ResponseBuilder.validation_error(
                            [{"field": "user_id", "message": "user_id is required."}]
                        )
                    )
                else:
                    svc = http.request.env["jabin.address.service"]
                    result = svc.set_default(address_id, user_id)
                    ctx.set_body(
                        ResponseBuilder.success(
                            data=result,
                            message="Default address set successfully",
                        )
                    )
            return ctx.response

else:  # pragma: no cover

    class AddressController(BaseApiController):  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""
