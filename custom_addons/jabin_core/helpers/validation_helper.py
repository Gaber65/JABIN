# -*- coding: utf-8 -*-
"""Generic validation helper for the JABIN platform.

This module provides **generic, non-domain** validation primitives that
controllers and services use to validate incoming payloads *before* the data
reaches the ORM layer. Domain-specific validators (Email, Phone, Password,
Price, Weight, UUID) live in the :mod:`jabin_core.validators` package and build
on top of these primitives.

Why a separate helper?
----------------------
The validators package is about *rules* (what a valid email looks like); this
helper is about *flow* (collecting multiple errors, checking required fields,
coercing types). Keeping them separate respects the Single Responsibility
Principle and makes both reusable in isolation.

Design
------
* :class:`ValidationHelper` is a namespace of static methods.
* :class:`ValidationResult` is a tiny accumulator that collects errors as a
  list of :class:`~jabin_core.utils.response_builder.ApiError` and reports
  success/failure. Controllers typically do::

      result = ValidationResult()
      result.require("email", payload.get("email"))
      result.require("password", payload.get("password"))
      if not result.ok:
          return ResponseBuilder.validation_error(result.errors)

* The helper deliberately raises nothing; it always reports errors via the
  result object so a single request can surface *all* field problems at once
  (better UX than failing on the first error).
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from ..utils.response_builder import ApiError


class ValidationResult:
    """Accumulator for validation errors found while inspecting a payload.

    Using an explicit result object (instead of raising on the first problem)
    lets the API return *all* field errors in one response, which is the UX the
    JABIN frontend expects.
    """

    __slots__ = ("_errors",)

    def __init__(self) -> None:
        self._errors: List[ApiError] = []

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def ok(self) -> bool:
        """``True`` when no errors have been recorded."""
        return not self._errors

    @property
    def errors(self) -> List[ApiError]:
        """The collected :class:`ApiError` list (empty when valid)."""
        return self._errors

    @property
    def has_errors(self) -> bool:
        """``True`` when at least one error has been recorded."""
        return bool(self._errors)

    # ------------------------------------------------------------------ #
    # Recording helpers
    # ------------------------------------------------------------------ #
    def add(self, message: str, field: Optional[str] = None) -> None:
        """Record a single error."""
        self._errors.append(ApiError(message=message, field=field))

    def add_error(self, error: ApiError) -> None:
        """Record an existing :class:`ApiError`."""
        self._errors.append(error)

    def merge(self, other: "ValidationResult") -> None:
        """Append all errors from ``other`` into this result."""
        self._errors.extend(other._errors)

    # ------------------------------------------------------------------ #
    # Field checks (convenience wrappers around ValidationHelper)
    # ------------------------------------------------------------------ #
    def require(self, field: str, value: Any, message: Optional[str] = None) -> None:
        """Record an error if ``value`` is missing/blank."""
        if ValidationHelper.is_missing(value):
            self.add(message or f"{field} is required.", field=field)

    def require_type(
        self, field: str, value: Any, expected_type: type, message: Optional[str] = None
    ) -> None:
        """Record an error if ``value`` is present but not of ``expected_type``."""
        if ValidationHelper.is_missing(value):
            return  # presence is checked separately via require()
        if not isinstance(value, expected_type):
            self.add(
                message or f"{field} must be a {expected_type.__name__}.",
                field=field,
            )

    def __repr__(self) -> str:  # pragma: no cover
        return f"ValidationResult(ok={self.ok}, errors={len(self._errors)})"


class ValidationHelper:
    """Generic, non-domain validation primitives."""

    # ------------------------------------------------------------------ #
    # Presence / type
    # ------------------------------------------------------------------ #
    @staticmethod
    def is_missing(value: Any) -> bool:
        """Return ``True`` for ``None``, empty string, or empty container."""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, tuple, dict, set)) and len(value) == 0:
            return True
        return False

    @staticmethod
    def is_present(value: Any) -> bool:
        """Inverse of :meth:`is_missing`."""
        return not ValidationHelper.is_missing(value)

    @staticmethod
    def is_int(value: Any) -> bool:
        """Return ``True`` if ``value`` is an int (bool excluded) or an int-string."""
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                int(value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def is_float(value: Any) -> bool:
        """Return ``True`` if ``value`` is a float/int (bool excluded) or numeric string."""
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def is_bool(value: Any) -> bool:
        """Return ``True`` for native bools or common truthy string spellings."""
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            return value.strip().lower() in {"true", "false", "1", "0", "yes", "no"}
        return False

    # ------------------------------------------------------------------ #
    # Length
    # ------------------------------------------------------------------ #
    @staticmethod
    def has_length(
        value: str, min_length: int = 0, max_length: Optional[int] = None
    ) -> bool:
        """Return ``True`` when ``len(value)`` is within ``[min_length, max_length]``."""
        if not isinstance(value, str):
            return False
        length = len(value)
        if length < min_length:
            return False
        if max_length is not None and length > max_length:
            return False
        return True

    @staticmethod
    def is_in_choices(value: Any, choices: Iterable[Any]) -> bool:
        """Return ``True`` when ``value`` is one of ``choices``."""
        return value in set(choices)

    # ------------------------------------------------------------------ #
    # Coercion (safe, return None on failure)
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Best-effort conversion to ``int``; returns ``default`` on failure."""
        if isinstance(value, bool):
            return int(value)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Best-effort conversion to ``float``; returns ``default`` on failure."""
        if isinstance(value, bool):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def to_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
        """Best-effort conversion to ``bool``; returns ``default`` on failure."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in {"true", "1", "yes"}:
                return True
            if lower in {"false", "0", "no"}:
                return False
        return default
