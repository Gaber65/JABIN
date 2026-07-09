# -*- coding: utf-8 -*-
"""Email validator for the JABIN platform.

Performs a pragmatic RFC-5321/5322-ish format check. It is intentionally not a
full RFC parser (those are notoriously permissive and offer little value);
instead we use a conservative regex that rejects obviously malformed addresses
while accepting all realistic ones.

Why not just rely on Odoo?
--------------------------
Odoo's ``fields.Char`` has no built-in email constraint, and even
``validate_email`` only checks format on specific fields. Centralising the rule
here means every module (users, orders, notifications, ...) applies the exact
same definition of "valid email".

Extensibility
-------------
* To enforce MX-record verification, add a classmethod that performs a DNS
  lookup and call it from the controller (kept out of Sprint 1 to avoid network
  dependency at the validation layer).
* To support plus-addressing quirks per tenant, subclass and override
  ``EMAIL_PATTERN``.
"""

from __future__ import annotations

import re
from typing import Optional

from ..helpers.validation_helper import ValidationResult, ValidationHelper

# Conservative email regex:
#  - local part: letters/digits/._%+- , 1..64 chars
#  - @
#  - domain: labels of letters/digits/hyphen, separated by dots, 1..255 chars
_EMAIL_REGEX = re.compile(
    r"^(?=.{1,254}$)"                          # total length <= 254
    r"(?P<local>[A-Za-z0-9._%+\-]{1,64})"
    r"@"
    r"(?P<domain>([A-Za-z0-9\-]+\.)+[A-Za-z]{2,})$"
)


class EmailValidator:
    """Stateless email-format validator."""

    EMAIL_PATTERN: str = _EMAIL_REGEX.pattern
    MAX_LENGTH: int = 254

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate(value: Optional[str], field: str = "email") -> ValidationResult:
        """Validate ``value`` and return a :class:`ValidationResult`.

        The result is empty (``ok == True``) when the email is valid, otherwise
        it contains a single :class:`ApiError` for ``field``.
        """
        result = ValidationResult()

        if ValidationHelper.is_missing(value):
            result.add(f"{field} is required.", field=field)
            return result

        email = str(value).strip().lower()

        if len(email) > EmailValidator.MAX_LENGTH:
            result.add(
                f"{field} must not exceed {EmailValidator.MAX_LENGTH} characters.",
                field=field,
            )
            return result

        if not _EMAIL_REGEX.match(email):
            result.add(f"{field} is not a valid email address.", field=field)

        return result

    @staticmethod
    def is_valid(value: Optional[str]) -> bool:
        """Boolean convenience wrapper around :meth:`validate`."""
        return EmailValidator.validate(value).ok

    @staticmethod
    def normalise(value: str) -> str:
        """Return a canonicalised email (trimmed + lowercased).

        Does **not** validate; callers should call :meth:`validate` first.
        """
        return value.strip().lower()
