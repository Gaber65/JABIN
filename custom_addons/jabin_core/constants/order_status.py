# -*- coding: utf-8 -*-
"""Order-status enum for the JABIN e-commerce platform.

Represents the lifecycle of a sales order from creation to completion (or
cancellation). Business modules will transition an order through these states
according to their own workflows; the enum itself holds no state-machine logic --
it only guarantees that the set of valid values is consistent everywhere.

Members
-------
PENDING        Order created but not yet confirmed (e.g. awaiting payment).
CONFIRMED      Order accepted and queued for fulfilment.
PROCESSING     Order being prepared (picking / packing).
SHIPPED        Order handed to the carrier.
DELIVERED      Order received by the customer.
COMPLETED      Order fully closed (delivered + paid + no open disputes).
CANCELLED      Order cancelled before fulfilment.
RETURNED       Order returned by the customer after delivery.
FAILED         Order failed irrecoverably (payment/fulfilment collapse).

Extensibility
-------------
Append new states only; never re-purpose existing values.
"""

from __future__ import annotations

from enum import Enum
from typing import List


class OrderStatus(str, Enum):
    """Lifecycle states of a sales order."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    FAILED = "failed"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @classmethod
    def all_values(cls) -> List[str]:
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "OrderStatus":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown order status '{value}'. "
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
    OrderStatus.PENDING: "Pending",
    OrderStatus.CONFIRMED: "Confirmed",
    OrderStatus.PROCESSING: "Processing",
    OrderStatus.SHIPPED: "Shipped",
    OrderStatus.DELIVERED: "Delivered",
    OrderStatus.COMPLETED: "Completed",
    OrderStatus.CANCELLED: "Cancelled",
    OrderStatus.RETURNED: "Returned",
    OrderStatus.FAILED: "Failed",
}
