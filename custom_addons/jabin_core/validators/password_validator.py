# -*- coding: utf-8 -*-
"""Password validator for the JABIN platform.

Enforces a configurable password strength policy. The defaults below are
deliberately moderate so they are acceptable for a Sprint-1 foundation; future
modules can subclass :class:`PasswordValidator` or pass different bounds to
implement stricter per-tenant policies.

Policy (defaults)
-----------------
* Length between ``MIN_LENGTH`` (8) and ``MAX_LENGTH`` (128).
* At least one lowercase letter.
* At least one uppercase letter.
* At least one digit.
* At least one special character from ``SPECIAL_CHARS``.

Design
------
* Validation never raises; it accumulates every failed rule into a single
  :class:`ValidationResult` so the API can list all policy violations at once.
* The validator **never** logs or stores the plaintext password; it only
  inspects it in memory.

Extensibility
-------------
* Add ``require_no_common_password(value)`` using a breached-password list.
* Add ``require_no_user_info(value, user_fields)`` to reject passwords that
  contain the user's name/email.
"""

from __future__ import annotations

import re
from typing import Optional

from ..helpers.validation_helper import ValidationResult, ValidationHelper


class PasswordValidator:
    """Configurable password-strength validator."""

    MIN_LENGTH: int = 8
    MAX_LENGTH: int = 128
    SPECIAL_CHARS: str = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`"

    # Pre-compiled rule patterns for performance.
    _LOWER = re.compile(r"[a-z]")
    _UPPER = re.compile(r"[A-Z]")
    _DIGIT = re.compile(r"\d")
    _SPECIAL = re.compile(rf"[{re.escape(SPECIAL_CHARS)}]")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate(value: Optional[str], field: str = "password") -> ValidationResult:
        """Validate ``value`` against the password policy.

        Every failed rule is added as a separate :class:`ApiError` so the
        response can tell the user exactly what to fix.
        """
        result = ValidationResult()

        if ValidationHelper.is_missing(value):
            result.add(f"{field} is required.", field=field)
            return result

        password = str(value)

        if len(password) < PasswordValidator.MIN_LENGTH:
            result.add(
                f"{field} must be at least {PasswordValidator.MIN_LENGTH} "
                f"characters long.",
                field=field,
            )
        if len(password) > PasswordValidator.MAX_LENGTH:
            result.add(
                f"{field} must not exceed {PasswordValidator.MAX_LENGTH} "
                f"characters.",
                field=field,
            )
        if not PasswordValidator._LOWER.search(password):
            result.add(f"{field} must contain at least one lowercase letter.", field=field)
        if not PasswordValidator._UPPER.search(password):
            result.add(f"{field} must contain at least one uppercase letter.", field=field)
        if not PasswordValidator._DIGIT.search(password):
            result.add(f"{field} must contain at least one digit.", field=field)
        if not PasswordValidator._SPECIAL.search(password):
            result.add(
                f"{field} must contain at least one special character "
                f"({PasswordValidator.SPECIAL_CHARS}).",
                field=field,
            )

        return result

    @staticmethod
    def is_valid(value: Optional[str]) -> bool:
        """Boolean convenience wrapper around :meth:`validate`."""
        return PasswordValidator.validate(value).ok

    @staticmethod
    def strength_score(value: str) -> int:
        """Return a coarse 0..5 score for UX meters (not a security guarantee).

        One point per satisfied rule (length>=MIN, length>=12, lower, upper,
        digit, special) -- capped at 5.
        """
        if not value:
            return 0
        score = 0
        if len(value) >= PasswordValidator.MIN_LENGTH:
            score += 1
        if len(value) >= 12:
            score += 1
        if PasswordValidator._LOWER.search(value):
            score += 1
        if PasswordValidator._UPPER.search(value):
            score += 1
        if PasswordValidator._DIGIT.search(value):
            score += 1
        if PasswordValidator._SPECIAL.search(value):
            score += 1
        return min(score, 5)
