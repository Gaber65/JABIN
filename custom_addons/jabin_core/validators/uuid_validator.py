# -*- coding: utf-8 -*-
"""UUID validator for the JABIN platform.

Validates that a string is a canonical UUID (any of the standard 8-4-4-4-12
hex formats). UUIDs are used for public-facing identifiers (order refs,
shipment tracking, API tokens) so that sequential integer IDs are never
exposed to clients.

Design
------
* Uses :class:`uuid.UUID` for parsing, which accepts all standard hyphenated
  and non-hyphenated forms and normalises them.
* Returns a :class:`ValidationResult`; never raises.
* :meth:`normalise` returns the canonical hyphenated lowercase string.

Extensibility
-------------
* Add ``validate_version(value, version=4)`` to restrict to a specific UUID
  variant once the token module lands.
"""

from __future__ import annotations

import uuid
from typing import Optional

from ..helpers.validation_helper import ValidationResult, ValidationHelper


class UUIDValidator:
    """Stateless UUID string validator."""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate(value: Optional[str], field: str = "uuid") -> ValidationResult:
        """Validate that ``value`` is a parseable UUID string."""
        result = ValidationResult()

        if ValidationHelper.is_missing(value):
            result.add(f"{field} is required.", field=field)
            return result

        raw = str(value).strip()

        try:
            uuid.UUID(raw)
        except (ValueError, AttributeError, TypeError):
            result.add(f"{field} is not a valid UUID.", field=field)

        return result

    @staticmethod
    def is_valid(value: Optional[str]) -> bool:
        """Boolean convenience wrapper around :meth:`validate`."""
        return UUIDValidator.validate(value).ok

    @staticmethod
    def normalise(value: str) -> str:
        """Return the canonical hyphenated lowercase UUID string.

        Example: ``"550E8300E29B41D4A716446655440000"`` ->
        ``"550e8300-e29b-41d4-a716-446655440000"``.
        Raises ``ValueError`` if ``value`` is not a valid UUID.
        """
        return str(uuid.UUID(str(value).strip()))

    @staticmethod
    def generate() -> str:
        """Generate a new random UUIDv4 string (canonical form)."""
        return str(uuid.uuid4())
