# -*- coding: utf-8 -*-
"""Base API controller for the JABIN platform.

Every JABIN REST controller inherits from :class:`BaseApiController`. The base
controller centralises the cross-cutting concerns that *every* endpoint shares:

1. **Content type** -- all responses are ``application/json``.
2. **Unified envelope** -- responses are built with
   :class:`~jabin_core.utils.response_builder.ResponseBuilder`.
3. **Exception handling** -- :class:`~jabin_core.utils.exception_mapper.ExceptionMapper`
   converts any raised exception into the envelope and an HTTP code, **without
   leaking stack traces** in production.
4. **JSON serialisation** -- :class:`~jabin_core.utils.json_helper.JsonHelper`
   handles ``Decimal`` / ``datetime`` / ``Enum`` transparently.
5. **Logging** -- a :class:`~jabin_core.utils.logger.JabinLogger` named after
   the controller records INFO/AUDIT/ERROR events with request context.
6. **JSON request parsing** -- :meth:`parse_json_body` safely decodes the
   incoming request body.

Design
------
The base controller is an :class:`odoo.http.Controller` subclass. It does **not**
declare any routes of its own -- those are added by subclasses (or by the
``api_root`` controller in this module). It exposes a single :meth:`_respond`
helper that subclasses use to serialise an envelope dict into an
:class:`odoo.http.Response`.

The :meth:`handle` context manager is the recommended way to wrap a handler
body so that exceptions are caught uniformly::

    @http.route("/api/v1/example", methods=["GET"], type="json", auth="none")
    def example(self, **kwargs):
        with self.handle() as ctx:
            ctx.set_body(ResponseBuilder.success(data={"hello": "world"}))
        return ctx.response

Subclasses may alternatively call :meth:`_respond` directly when they handle
errors themselves.

Extensibility
-------------
* When JWT auth lands, override :meth:`_current_user` to resolve the user from
  the token instead of the session.
* When CORS / rate-limiting are needed, they can be layered into
  :meth:`_build_response` or a decorator without touching every endpoint.
"""

from __future__ import annotations

import contextlib
import json as _stdlib_json
from typing import Any, Dict, Optional

try:
    from odoo import http  # type: ignore
    from odoo.http import request, Response  # type: ignore
    _ODOO = True
except Exception:  # pragma: no cover - non-Odoo test environment
    _ODOO = False
    http = None  # type: ignore
    request = None  # type: ignore
    Response = None  # type: ignore

from jabin_core import ResponseBuilder, ExceptionMapper, JabinLogger, JsonHelper


# ---------------------------------------------------------------------------
# Handler context object
# ---------------------------------------------------------------------------
class _HandlerContext:
    """Mutable context handed to controllers inside the ``handle`` block.

    It carries the envelope to serialise and builds the final
    :class:`odoo.http.Response` on exit. Keeping it as a small object (instead
    of returning tuples) lets controllers set the body, status, and meta in a
    readable, order-independent way.
    """

    __slots__ = ("_envelope", "_status", "_headers", "controller")

    def __init__(self, controller: "BaseApiController") -> None:
        self.controller = controller
        self._envelope: Dict[str, Any] = ResponseBuilder.success()
        self._status: int = 200
        self._headers: Dict[str, str] = {}

    # -- setters ------------------------------------------------------- #
    def set_body(self, envelope: Dict[str, Any], status: Optional[int] = None) -> None:
        """Set the response envelope and optionally override the HTTP status."""
        self._envelope = envelope
        if status is not None:
            self._status = status
        else:
            # Infer status from the envelope "code" field when present.
            self._status = int(envelope.get("code", 200))

    def set_status(self, status: int) -> None:
        self._status = status

    def add_header(self, name: str, value: str) -> None:
        self._headers[name] = value

    # -- properties ---------------------------------------------------- #
    @property
    def envelope(self) -> Dict[str, Any]:
        return self._envelope

    @property
    def status(self) -> int:
        return self._status

    @property
    def response(self):  # type: ignore[override]
        """Build and return the :class:`odoo.http.Response`."""
        return self.controller._build_response(
            self._envelope, self._status, self._headers
        )


# ---------------------------------------------------------------------------
# Base controller
# ---------------------------------------------------------------------------
if _ODOO:

    class BaseApiController(http.Controller):
        """Foundation controller for every JABIN REST endpoint.

        Subclasses inherit the unified envelope, JSON serialisation, and
        exception handling without re-implementing them.
        """

        # Public API version prefix. Centralised so version bumps happen here.
        API_PREFIX: str = "/api/v1"

        # ------------------------------------------------------------------ #
        # Construction-time logger
        # ------------------------------------------------------------------ #
        @classmethod
        def _logger(cls):
            """Return a logger named after the controller class."""
            return JabinLogger.get(
                f"api.{cls.__name__}",
                context={"controller": cls.__name__},
            )

        # ------------------------------------------------------------------ #
        # JSON helpers
        # ------------------------------------------------------------------ #
        @staticmethod
        def parse_json_body() -> Dict[str, Any]:
            """Parse the JSON body of the current request.

            Returns an empty dict when the body is absent or not JSON. Callers
            validate the resulting dict with the validators package.
            """
            try:
                data = request.get_json_data()
            except Exception:
                data = None
            if data is None:
                return {}
            if isinstance(data, dict):
                return data
            if isinstance(data, (bytes, bytearray, str)):
                try:
                    parsed = JsonHelper.loads(data)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
            return {}

        # ------------------------------------------------------------------ #
        # Response building
        # ------------------------------------------------------------------ #
        @classmethod
        def _build_response(
            cls,
            envelope: Dict[str, Any],
            status: int,
            extra_headers: Optional[Dict[str, str]] = None,
        ):
            """Serialise ``envelope`` into an ``application/json`` Response.

            Uses :class:`JsonHelper` so ``Decimal`` / ``datetime`` / ``Enum``
            values are handled correctly.
            """
            body = JsonHelper.dumps(envelope)
            headers = {"Content-Type": "application/json"}
            if extra_headers:
                headers.update(extra_headers)
            return Response(body, status=status, headers=headers)

        @classmethod
        def _respond(
            cls,
            envelope: Dict[str, Any],
            status: Optional[int] = None,
            extra_headers: Optional[Dict[str, str]] = None,
        ):
            """Convenience wrapper: serialise an envelope into a Response.

            The HTTP status is inferred from ``envelope["code"]`` unless
            ``status`` is explicitly provided.
            """
            if status is None:
                status = int(envelope.get("code", 200))
            return cls._build_response(envelope, status, extra_headers)

        # ------------------------------------------------------------------ #
        # Exception-handling context manager
        # ------------------------------------------------------------------ #
        @classmethod
        @contextlib.contextmanager
        def handle(cls):
            """Context manager that catches exceptions and maps them.

            Usage::

                @http.route(...)
                def my_endpoint(self, **kw):
                    with self.handle() as ctx:
                        ctx.set_body(ResponseBuilder.success(data=...))
                    return ctx.response

            If the block raises, the exception is converted into an error
            envelope via :class:`ExceptionMapper` and the response is built
            from that envelope. The stack trace is logged but never sent to
            the client.
            """
            ctx = _HandlerContext(cls)  # type: ignore[arg-type]
            logger = cls._logger()
            try:
                yield ctx
            except Exception as exc:  # noqa: BLE001 - intentional broad catch
                envelope, code = ExceptionMapper.handle(
                    exc,
                    logger=logger,
                    context={"endpoint": getattr(request, "httprequest", None)
                             and request.httprequest.path},
                )
                ctx.set_body(envelope, status=code)
            # The caller reads ctx.response after the block.

        # ------------------------------------------------------------------ #
        # Auth placeholders (wired in a later sprint)
        # ------------------------------------------------------------------ #
        @classmethod
        def _current_user(cls):
            """Return the current authenticated user (placeholder).

            Sprint 1 returns ``None`` because no auth is implemented yet.
            The JWT sprint will override this to resolve the user from the
            bearer token.
            """
            return None

else:  # pragma: no cover - non-Odoo test environment

    class BaseApiController:  # type: ignore[no-redef]
        """Placeholder used when Odoo is not importable (unit-test context)."""

        API_PREFIX: str = "/api/v1"
