# -*- coding: utf-8 -*-
"""API root controller for the JABIN platform.

Registers the discoverable ``GET /api/v1/`` endpoint. In Sprint 1 this endpoint
is intentionally minimal: it returns platform metadata (name, version, status)
and an **empty** list of available resources, ready to be populated as
business modules are added in later sprints.

Why a root endpoint?
--------------------
* **Discoverability** -- clients can ``GET /api/v1/`` to learn the API version
  and the list of available top-level resources without reading out-of-band
  documentation.
* **Health signal** -- returning a 200 here proves the API gateway and the
  ``jabin_core`` infrastructure are wired up correctly. It is a lightweight
  liveness probe (a dedicated ``/health`` can be added later for readiness).

Extensibility
-------------
* As business modules land, append their resource names to
  :attr:`ApiRootController.RESOURCES` (or, better, make it dynamic by scanning
  registered routes) so the root always reflects what is actually deployed.
* A ``/api/v1/health`` endpoint can be added here or in a dedicated controller
  once DB / cache probes are needed.
"""

from __future__ import annotations

from typing import Any, Dict, List

try:
    from odoo import http  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover
    _ODOO = False
    http = None  # type: ignore

from jabin_core import ResponseBuilder

from .base import BaseApiController


if _ODOO:

    class ApiRootController(BaseApiController):
        """Discoverable root for the JABIN REST API (``/api/v1/``)."""

        # Static platform metadata. Centralised so a version bump touches one
        # place. In a later sprint this can be sourced from the module manifest
        # or a config parameter.
        PLATFORM_NAME: str = "JABIN"
        API_VERSION: str = "v1"
        PLATFORM_VERSION: str = "17.0.1.0.0"
        STATUS: str = "online"

        # Resources advertised at the root. Empty in Sprint 1; populated as
        # business modules are added.
        RESOURCES: List[str] = []

        # ------------------------------------------------------------------ #
        # Routes
        # ------------------------------------------------------------------ #
        @http.route(
            ["/api/v1/", "/api/v1"],
            methods=["GET"],
            type="http",
            auth="none",
            csrf=False,
        )
        def api_root(self, **kwargs: Any):
            """Return platform metadata and the list of available resources.

            Response shape (success)::

                {
                    "success": true,
                    "message": "Success",
                    "code": 200,
                    "data": {
                        "platform": "JABIN",
                        "api_version": "v1",
                        "platform_version": "17.0.1.0.0",
                        "status": "online",
                        "resources": []
                    },
                    "meta": {},
                    "errors": []
                }
            """
            with self.handle() as ctx:
                data: Dict[str, Any] = {
                    "platform": self.PLATFORM_NAME,
                    "api_version": self.API_VERSION,
                    "platform_version": self.PLATFORM_VERSION,
                    "status": self.STATUS,
                    "resources": list(self.RESOURCES),
                }
                ctx.set_body(
                    ResponseBuilder.success(
                        data=data,
                        message="Welcome to the JABIN API",
                    )
                )
            return ctx.response

else:  # pragma: no cover - non-Odoo test environment

    class ApiRootController(BaseApiController):  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""

        PLATFORM_NAME: str = "JABIN"
        API_VERSION: str = "v1"
        RESOURCES: List[str] = []
