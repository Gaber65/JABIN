# -*- coding: utf-8 -*-
"""User-type enum for the JABIN platform.

This enum classifies every account that can authenticate against the platform.
Business modules (e.g. ``jabin_users``, ``jabin_orders``) will reference
``UserType`` instead of hard-coded strings, guaranteeing referential integrity
across the whole codebase and the database.

Members
-------
ADMIN     Platform administrator. Full access to every module and record.
CUSTOMER  End-customer who places orders on the e-commerce storefront.
MANAGER   Operational manager with elevated but scoped permissions.
EMPLOYEE  Internal staff member (warehouse, support, finance, ...).
DRIVER    Delivery driver fulfilling shipment orders.

Extensibility
-------------
Append new members (e.g. ``VENDOR = "vendor"``) at the bottom of the class.
Never re-order or re-number existing members.
"""

from __future__ import annotations

from enum import Enum
from typing import List


class UserType(str, Enum):
    """Enumeration of platform user types (stored as ``str`` for JSON-friendliness)."""

    ADMIN = "admin"
    CUSTOMER = "customer"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    DRIVER = "driver"

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    @property
    def label(self) -> str:
        """Human-readable label suitable for UI / API responses."""
        return _LABELS[self]

    @classmethod
    def all_values(cls) -> List[str]:
        """Return the list of raw string values (handy for API validation)."""
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "UserType":
        """Convert a raw string into a ``UserType``.

        Raises
        ------
        ValueError
            If ``value`` is not a known user type.
        """
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown user type '{value}'. "
                f"Valid values: {cls.all_values()}"
            ) from exc

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Return ``True`` when ``value`` corresponds to a known user type."""
        try:
            cls(value)
            return True
        except ValueError:
            return False


# Private label map kept separate so the enum stays declarative.
_LABELS: dict = {
    UserType.ADMIN: "Administrator",
    UserType.CUSTOMER: "Customer",
    UserType.MANAGER: "Manager",
    UserType.EMPLOYEE: "Employee",
    UserType.DRIVER: "Driver",
}
