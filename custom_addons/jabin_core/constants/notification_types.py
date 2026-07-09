# -*- coding: utf-8 -*-
"""Notification-type enum for the JABIN platform.

Categorises every notification the platform can emit (push, email, SMS,
in-app). The future notification module will use this enum to route messages
to the correct channel and to let users tune their preferences per type.

Members
-------
ORDER          Order lifecycle notifications (confirmed, shipped, delivered).
PAYMENT        Payment-related notifications (paid, refund, failure).
DELIVERY       Delivery / shipment tracking notifications.
PROMOTION      Marketing / promotional notifications.
SYSTEM         Platform-wide system notifications (maintenance, security).
ACCOUNT        Account lifecycle notifications (welcome, password reset).
STOCK          Stock / availability alerts (back-in-stock, low-stock).

Extensibility
-------------
Append new types only.
"""

from __future__ import annotations

from enum import Enum
from typing import List


class NotificationType(str, Enum):
    """Category of a platform notification."""

    ORDER = "order"
    PAYMENT = "payment"
    DELIVERY = "delivery"
    PROMOTION = "promotion"
    SYSTEM = "system"
    ACCOUNT = "account"
    STOCK = "stock"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @classmethod
    def all_values(cls) -> List[str]:
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "NotificationType":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown notification type '{value}'. "
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
    NotificationType.ORDER: "Order",
    NotificationType.PAYMENT: "Payment",
    NotificationType.DELIVERY: "Delivery",
    NotificationType.PROMOTION: "Promotion",
    NotificationType.SYSTEM: "System",
    NotificationType.ACCOUNT: "Account",
    NotificationType.STOCK: "Stock",
}
