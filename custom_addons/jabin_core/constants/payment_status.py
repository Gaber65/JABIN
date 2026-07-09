# -*- coding: utf-8 -*-
"""Payment-status enum for the JABIN platform.

Tracks the financial state of an order / invoice independently from the
physical delivery state. This separation allows the system to model
real-world flows such as "delivered but still pending payment" or "paid but
not yet shipped".

Members
-------
UNPAID      No payment has been registered yet.
PENDING     Payment initiated but not yet confirmed (gateway in progress).
PAID        Payment fully captured.
PARTIALLY_PAID  Only part of the amount has been captured.
REFUNDED    Full amount refunded to the customer.
PARTIALLY_REFUNDED  Only part of the amount has been refunded.
FAILED      Payment attempt failed.
CANCELLED   Payment cancelled before capture.

Extensibility
-------------
Append new states only.
"""

from __future__ import annotations

from enum import Enum
from typing import List


class PaymentStatus(str, Enum):
    """Financial state of an order / invoice."""

    UNPAID = "unpaid"
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @classmethod
    def all_values(cls) -> List:
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "PaymentStatus":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown payment status '{value}'. "
                f"Valid values: {cls.all_values()}"
            ) from exc

    @classmethod
    def has_value(cls, value: str) -> bool:
        try:
            cls(value)
            return True
        except ValueError:
            return False


_LABELS: dict = {
    PaymentStatus.UNPAID: "Unpaid",
    PaymentStatus.PENDING: "Pending",
    PaymentStatus.PAID: "Paid",
    PaymentStatus.PARTIALLY_PAID: "Partially Paid",
    PaymentStatus.REFUNDED: "Refunded",
    PaymentStatus.PARTIALLY_REFUNDED: "Partially Refunded",
    PaymentStatus.FAILED: "Failed",
    PaymentStatus.CANCELLED: "Cancelled",
}
