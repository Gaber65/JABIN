# -*- coding: utf-8 -*-
"""Price validator for the JABIN platform.

Validates monetary values submitted by API clients. Monetary correctness is
critical for an e-commerce ERP, so this validator:

* Accepts ``int``, ``float``, ``str`` (numeric) and ``Decimal`` inputs.
* Rejects negative values.
* Rejects values exceeding ``MAX_VALUE`` (guards against absurd inputs).
* Rejects more than ``MAX_DECIMAL_PLACES`` fractional digits (typical currency
  precision is 2; some currencies use 3).

Design
------
* Internally works with :class:`decimal.Decimal` to avoid float rounding
  surprises (e.g. ``0.1 + 0.2``).
* Returns a :class:`ValidationResult`; never raises.

Extensibility
-------------
* Per-currency decimal precision can be enforced by passing a ``currency``
  parameter once the currency module exists.
"""

from __future__ import annotations

import decimal
import re
from typing import Optional, Union

from ..helpers.validation_helper import ValidationResult, ValidationHelper

# Numeric string regex: optional sign, digits, optional dot + digits.
_NUMERIC_STR = re.compile(r"^-?\d+(\.\d+)?$")


class PriceValidator:
    """Monetary value validator (non-negative, bounded precision)."""

    MAX_VALUE: decimal.Decimal = decimal.Decimal("1000000000")  # 1,000,000,000.00
    MAX_DECIMAL_PLACES: int = 2

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate(
        value: Optional[Union[int, float, str, decimal.Decimal]],
        field: str = "price",
    ) -> ValidationResult:
        """Validate a monetary ``value``."""
        result = ValidationResult()

        if ValidationHelper.is_missing(value):
            result.add(f"{field} is required.", field=field)
            return result

        decimal_value = PriceValidator._to_decimal(value, field, result)
        if decimal_value is None:
            return result  # conversion error already recorded

        if decimal_value < 0:
            result.add(f"{field} must not be negative.", field=field)

        if decimal_value > PriceValidator.MAX_VALUE:
            result.add(
                f"{field} must not exceed {PriceValidator.MAX_VALUE}.",
                field=field,
            )

        # Decimal-places check (only meaningful for non-integer strings).
        if isinstance(value, str) and "." in value:
            places = len(value.split(".", 1)[1])
            if places > PriceValidator.MAX_DECIMAL_PLACES:
                result.add(
                    f"{field} must not have more than "
                    f"{PriceValidator.MAX_DECIMAL_PLACES} decimal places.",
                    field=field,
                )

        return result

    @staticmethod
    def is_valid(value: Optional[Union[int, float, str, decimal.Decimal]]) -> bool:
        """Boolean convenience wrapper around :meth:`validate`."""
        return PriceValidator.validate(value).ok

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_decimal(
        value: Union[int, float, str, decimal.Decimal],
        field: str,
        result: ValidationResult,
    ) -> Optional[decimal.Decimal]:
        """Safely convert ``value`` to :class:`Decimal`, recording errors."""
        try:
            if isinstance(value, bool):
                raise TypeError("boolean is not a valid price")
            if isinstance(value, decimal.Decimal):
                return value
            if isinstance(value, int):
                return decimal.Decimal(value)
            if isinstance(value, float):
                # Convert via str to avoid float repr noise (e.g. 0.1).
                return decimal.Decimal(str(value))
            if isinstance(value, str):
                stripped = value.strip()
                if not _NUMERIC_STR.match(stripped):
                    raise ValueError("not a numeric string")
                return decimal.Decimal(stripped)
            raise TypeError(f"unsupported type {type(value).__name__}")
        except (ValueError, TypeError, decimal.InvalidOperation):
            result.add(f"{field} must be a valid numeric value.", field=field)
            return None

    @staticmethod
    def to_decimal(
        value: Union[int, float, str, decimal.Decimal]
    ) -> decimal.Decimal:
        """Convert to :class:`Decimal` (assumes already validated).

        Raises if the value cannot be converted; callers should run
        :meth:`validate` first.
        """
        if isinstance(value, decimal.Decimal):
            return value
        if isinstance(value, int):
            return decimal.Decimal(value)
        if isinstance(value, float):
            return decimal.Decimal(str(value))
        return decimal.Decimal(str(value).strip())
