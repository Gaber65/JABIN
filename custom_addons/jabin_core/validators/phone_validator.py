# -*- coding: utf-8 -*-
"""Phone validator for the JABIN platform.

Accepts international phone numbers in E.164-ish form. The rule is deliberately
permissive (digits, spaces, hyphens, parentheses, optional leading ``+``) and
then normalises the result to a compact, digits-only representation that the
future ``jabin_users`` module can store consistently.

Why not a heavy dependency?
---------------------------
Full phone validation (libphonenumber) is powerful but heavyweight and
region-dependent. For Sprint 1 we provide a structure that is good enough to
reject junk while leaving room to plug in libphonenumber later behind the same
``validate`` / ``is_valid`` / ``normalise`` API.

Extensibility
-------------
* Replace the regex/normalisation with a ``phonenumbers``-backed
  implementation without changing call sites.
* Add a ``region`` parameter to ``validate`` for locale-specific rules.
"""

from __future__ import annotations

import re
from typing import Optional

from ..helpers.validation_helper import ValidationResult, ValidationHelper

# Allow +, digits, spaces, hyphens, parentheses. We then count digits.
_PHONE_REGEX = re.compile(r"^\+?[\d\s\-\(\)]+$")


class PhoneValidator:
    """Stateless phone-number validator (E.164-ish)."""

    MIN_DIGITS: int = 7
    MAX_DIGITS: int = 15  # E.164 maximum

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate(value: Optional[str], field: str = "phone") -> ValidationResult:
        """Validate ``value`` and return a :class:`ValidationResult`."""
        result = ValidationResult()

        if ValidationHelper.is_missing(value):
            result.add(f"{field} is required.", field=field)
            return result

        raw = str(value).strip()

        if not _PHONE_REGEX.match(raw):
            result.add(
                f"{field} may only contain digits, spaces, hyphens, "
                f"parentheses and an optional leading '+'.",
                field=field,
            )
            return result

        digits = PhoneValidator.normalise(raw)
        digit_count = len(digits.lstrip("+"))

        if digit_count < PhoneValidator.MIN_DIGITS:
            result.add(
                f"{field} must contain at least {PhoneValidator.MIN_DIGITS} digits.",
                field=field,
            )
        elif digit_count > PhoneValidator.MAX_DIGITS:
            result.add(
                f"{field} must contain at most {PhoneValidator.MAX_DIGITS} digits.",
                field=field,
            )

        return result

    @staticmethod
    def is_valid(value: Optional[str]) -> bool:
        """Boolean convenience wrapper around :meth:`validate`."""
        return PhoneValidator.validate(value).ok

    @staticmethod
    def normalise(value: str) -> str:
        """Return the phone number stripped of non-digit chars (keeps a leading ``+``).

        Example: ``"+1 (234) 567-8900"`` -> ``"+12345678900"``.
        Does **not** validate; callers should call :meth:`validate` first.
        """
        raw = value.strip()
        leading_plus = "+" if raw.startswith("+") else ""
        digits = re.sub(r"\D", "", raw)
        return f"{leading_plus}{digits}"
