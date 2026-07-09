# -*- coding: utf-8 -*-
"""Stock-status enum for the JABIN platform.

Represents the availability state of a product / SKU in a warehouse. Used by
the future inventory module and surfaced to the storefront so customers see
accurate availability.

Members
-------
IN_STOCK        Quantity on hand >= reorder threshold.
LOW_STOCK       Quantity on hand > 0 but below the reorder threshold.
OUT_OF_STOCK    Quantity on hand == 0.
BACKORDERED     Out of stock but still orderable (will be fulfilled later).
DISCONTINUED    Product permanently retired; no longer orderable.

Extensibility
-------------
Append new states only.
"""

from __future__ import annotations

from enum import Enum
from typing import List


class StockStatus(str, Enum):
    """Availability state of a product / SKU."""

    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    BACKORDERED = "backordered"
    DISCONTINUED = "discontinued"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @classmethod
    def all_values(cls) -> List[str]:
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "StockStatus":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown stock status '{value}'. "
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
    StockStatus.IN_STOCK: "In Stock",
    StockStatus.LOW_STOCK: "Low Stock",
    StockStatus.OUT_OF_STOCK: "Out of Stock",
    StockStatus.BACKORDERED: "Backordered",
    StockStatus.DISCONTINUED: "Discontinued",
}
