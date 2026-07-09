# -*- coding: utf-8 -*-
"""Pagination helper for the JABIN platform.

Produces the standard ``meta`` block that every list endpoint embeds in the
JABIN JSON envelope::

    "meta": {
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total_items": 134,
            "total_pages": 7,
            "has_next": true,
            "has_prev": false
        }
    }

Why a dedicated helper?
-----------------------
Pagination arithmetic is duplicated endlessly if not centralised. Putting it in
one place guarantees every list endpoint speaks the same pagination dialect,
which is essential for frontends that render generic data tables.

Design
------
* The helper is **pure**: it never touches the database. Callers pass the
  already-known ``total_items`` count (obtained from a ``search_count`` or
  SQL ``COUNT``) and the requested ``page`` / ``per_page``.
* Limits are clamped to sane bounds to protect the database from pathological
  requests (``per_page=1000000``).
* :meth:`offset_limit` returns the ``(offset, limit)`` pair ready to feed into
  Odoo's ``search(..., offset=..., limit=...)`` or a SQL ``LIMIT/OFFSET``.

Extensibility
-------------
* Cursor-based pagination can be added later as a sibling class
  (``CursorPaginationHelper``) without changing the offset-based one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

# Hard limits to protect the DB from abusive requests.
DEFAULT_PER_PAGE: int = 20
MAX_PER_PAGE: int = 100
MIN_PAGE: int = 1


@dataclass(frozen=True)
class PaginationMeta:
    """Immutable value object describing a page of results."""

    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

    def to_dict(self) -> Dict[str, object]:
        """Serialise into the ``meta.pagination`` block."""
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class PaginationHelper:
    """Offset/limit pagination arithmetic (pure, no DB access)."""

    # ------------------------------------------------------------------ #
    # Normalisation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise(page: int, per_page: int) -> Tuple[int, int]:
        """Clamp page/per_page to valid bounds."""
        if page is None or page < MIN_PAGE:
            page = MIN_PAGE
        if per_page is None or per_page < 1:
            per_page = DEFAULT_PER_PAGE
        if per_page > MAX_PER_PAGE:
            per_page = MAX_PER_PAGE
        return page, per_page

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def build(
        total_items: int,
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> PaginationMeta:
        """Compute the pagination metadata for a list endpoint.

        Parameters
        ----------
        total_items:
            Total number of records matching the query (from ``search_count``).
        page:
            1-based page number requested by the client.
        per_page:
            Page size requested by the client (clamped to ``MAX_PER_PAGE``).
        """
        page, per_page = PaginationHelper._normalise(page, per_page)
        total_items = max(int(total_items), 0)

        # ceil division for total pages, with at least 1 page even when empty.
        total_pages = (total_items + per_page - 1) // per_page if per_page else 1
        if total_pages < 1:
            total_pages = 1

        has_next = page < total_pages
        has_prev = page > 1

        return PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    @staticmethod
    def offset_limit(page: int, per_page: int) -> Tuple[int, int]:
        """Return ``(offset, limit)`` for ``search()`` / SQL.

        Useful when the caller only needs the query bounds and not the full
        metadata block.
        """
        page, per_page = PaginationHelper._normalise(page, per_page)
        offset = (page - 1) * per_page
        return offset, per_page

    @staticmethod
    def meta_dict(
        total_items: int,
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Dict[str, object]:
        """Convenience: return the ready-to-embed ``{"pagination": {...}}`` dict.

        This is the shape that goes directly into ``ResponseBuilder.success(
        ..., meta=PaginationHelper.meta_dict(...))``.
        """
        return {"pagination": PaginationHelper.build(
            total_items, page, per_page
        ).to_dict()}
