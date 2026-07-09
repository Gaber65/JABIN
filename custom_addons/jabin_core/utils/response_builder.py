# -*- coding: utf-8 -*-
"""Unified API response builder for the JABIN platform.

Every REST endpoint -- no matter the module -- must return the exact same JSON
envelope so that clients (web, mobile, third-party integrations) can rely on a
single parsing contract.

Canonical envelope
------------------

Success::

    {
        "success": true,
        "message": "Success",
        "code": 200,
        "data": {},
        "meta": {},
        "errors": []
    }

Validation error::

    {
        "success": false,
        "message": "Validation Error",
        "code": 400,
        "data": null,
        "meta": {},
        "errors": [
            {"field": "email", "message": "Email already exists"}
        ]
    }

Server error::

    {
        "success": false,
        "message": "Internal Server Error",
        "code": 500,
        "data": null,
        "meta": {},
        "errors": []
    }

Design notes
------------
* ``ApiError`` is a tiny value object so callers build errors declaratively
  rather than fiddling with dicts.
* ``ResponseBuilder`` methods are all ``@staticmethod`` / ``@classmethod``
  because the envelope is stateless; instantiation is therefore unnecessary.
* The builder only *produces dicts*; it never touches the HTTP layer. The
  ``jabin_api`` controllers are responsible for serialising the dict with
  ``json``/``JsonHelper`` and setting the HTTP status. This keeps the builder
  reusable outside of an HTTP context (e.g. RPC, tests, queues).
* ``meta`` is always present (even if empty) so clients can safely read
  ``response["meta"]`` without a ``KeyError``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# Structured error value object
# ---------------------------------------------------------------------------


class ApiError:
    """Declarative representation of a single API error.

    Parameters
    ----------
    message:
        Human-readable explanation of the error (always required).
    field:
        Name of the request field the error relates to. ``None`` for
        non-field (global) errors.

    Rationale
    ---------
    Wrapping the ``{"field": ..., "message": ...}`` shape in a class gives us
    type safety, IDE auto-complete, and a single place to evolve the error
    schema (e.g. adding an ``error_code`` later) without touching every
    call site.
    """

    __slots__ = ("field", "message")

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        if not message or not isinstance(message, str):
            raise ValueError("ApiError requires a non-empty 'message' string.")
        self.field: Optional[str] = field
        self.message: str = message

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Serialise into the canonical ``{"field", "message"}`` dict."""
        return {"field": self.field, "message": self.message}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ApiError(field={self.field!r}, message={self.message!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApiError):
            return NotImplemented
        return self.field == other.field and self.message == other.message


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class ResponseBuilder:
    """Stateless factory for the canonical JABIN JSON response envelope.

    All public methods return a plain ``dict`` ready for ``json.dumps``.
    The class is intentionally framework-agnostic so it can be unit-tested in
    isolation and reused outside of Odoo controllers.
    """

    # Standardised, human-readable messages for the most common HTTP codes.
    # Centralising them here prevents subtle wording drift between modules.
    _DEFAULT_MESSAGES: Dict[int, str] = {
        200: "Success",
        201: "Created",
        202: "Accepted",
        204: "No Content",
        400: "Validation Error",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
    }

    # ------------------------------------------------------------------ #
    # Internal helper
    # ------------------------------------------------------------------ #
    @classmethod
    def _message_for(cls, code: int, message: Optional[str]) -> str:
        """Return the message to use, falling back to the default for ``code``."""
        if message:
            return message
        return cls._DEFAULT_MESSAGES.get(code, "Error")

    @classmethod
    def _envelope(
        cls,
        *,
        success: bool,
        code: int,
        message: Optional[str],
        data: Optional[Any],
        meta: Optional[Dict[str, Any]],
        errors: Optional[List[Union[ApiError, Dict[str, Any]]]],
    ) -> Dict[str, Any]:
        """Assemble the canonical envelope dict.

        Normalises ``errors`` entries: accepts both :class:`ApiError` and raw
        dicts so callers can use whichever is more convenient.
        """
        normalised_errors: List[Dict[str, Optional[str]]] = []
        if errors:
            for err in errors:
                if isinstance(err, ApiError):
                    normalised_errors.append(err.to_dict())
                elif isinstance(err, dict):
                    normalised_errors.append(
                        {
                            "field": err.get("field"),
                            "message": err.get("message", ""),
                        }
                    )
                else:
                    raise TypeError(
                        f"Unsupported error entry type: {type(err).__name__}"
                    )

        return {
            "success": success,
            "message": cls._message_for(code, message),
            "code": code,
            "data": data if data is not None else ({} if success else None),
            "meta": meta if meta is not None else {},
            "errors": normalised_errors,
        }

    # ------------------------------------------------------------------ #
    # Success builders
    # ------------------------------------------------------------------ #
    @staticmethod
    def success(
        data: Any = None,
        message: Optional[str] = None,
        code: int = 200,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a success envelope (``success: true``).

        Parameters
        ----------
        data:
            The payload to return. Defaults to ``{}`` when omitted.
        message:
            Override the default message for ``code``.
        code:
            HTTP-ish status code (2xx). Defaults to ``200``.
        meta:
            Optional metadata (pagination, counts, ...). Defaults to ``{}``.
        """
        return ResponseBuilder._envelope(
            success=True,
            code=code,
            message=message,
            data=data,
            meta=meta,
            errors=None,
        )

    @staticmethod
    def created(
        data: Any = None,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for ``201 Created`` success responses."""
        return ResponseBuilder.success(
            data=data, message=message, code=201, meta=meta
        )

    @staticmethod
    def accepted(
        data: Any = None,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for ``202 Accepted`` (async) success responses."""
        return ResponseBuilder.success(
            data=data, message=message, code=202, meta=meta
        )

    # ------------------------------------------------------------------ #
    # Error builders
    # ------------------------------------------------------------------ #
    @staticmethod
    def error(
        message: Optional[str] = None,
        code: int = 400,
        errors: Optional[List[Union[ApiError, Dict[str, Any]]]] = None,
        data: Any = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a generic error envelope (``success: false``).

        Use this for non-validation errors (404, 409, 500, ...). For
        field-level validation errors prefer :meth:`validation_error`.
        """
        return ResponseBuilder._envelope(
            success=False,
            code=code,
            message=message,
            data=data,
            meta=meta,
            errors=errors,
        )

    @staticmethod
    def validation_error(
        errors: List[Union[ApiError, Dict[str, Any]]],
        message: str = "Validation Error",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a ``400`` validation-error envelope.

        ``errors`` must be a non-empty list of :class:`ApiError` or dicts.
        """
        if not errors:
            raise ValueError(
                "validation_error requires a non-empty 'errors' list."
            )
        return ResponseBuilder._envelope(
            success=False,
            code=400,
            message=message,
            data=None,
            meta=meta,
            errors=errors,
        )

    @staticmethod
    def not_found(
        message: str = "Resource not found",
        errors: Optional[List[Union[ApiError, Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Build a ``404`` error envelope."""
        return ResponseBuilder.error(message=message, code=404, errors=errors)

    @staticmethod
    def unauthorized(
        message: str = "Authentication required",
        errors: Optional[List[Union[ApiError, Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Build a ``401`` error envelope."""
        return ResponseBuilder.error(message=message, code=401, errors=errors)

    @staticmethod
    def forbidden(
        message: str = "Access denied",
        errors: Optional[List[Union[ApiError, Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Build a ``403`` error envelope."""
        return ResponseBuilder.error(message=message, code=403, errors=errors)

    @staticmethod
    def server_error(
        message: str = "Internal Server Error",
        errors: Optional[List[Union[ApiError, Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Build a ``500`` error envelope.

        Stack traces must never be appended here; the
        :class:`~jabin_core.utils.exception_mapper.ExceptionMapper` is
        responsible for logging them while keeping the payload clean.
        """
        return ResponseBuilder.error(message=message, code=500, errors=errors)
