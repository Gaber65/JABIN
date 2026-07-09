# -*- coding: utf-8 -*-
"""String helper for the JABIN platform.

A collection of small, pure functions for the string manipulations that recur
across an ERP codebase: slugification, truncation, camelCase/snake_case
conversion, whitespace normalisation, masking of sensitive data.

Why centralise?
---------------
These operations are tiny but appear in dozens of places (URL slugs, log
masking, JSON key normalisation, UI previews). Duplicating them invites
inconsistent behaviour (e.g. one slugify strips accents, another doesn't).

All methods are static; the class acts as a namespace and is free of Odoo
dependencies.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


class StringHelper:
    """Common string utilities used across the platform."""

    # ------------------------------------------------------------------ #
    # Slugification
    # ------------------------------------------------------------------ #
    @staticmethod
    def slugify(value: str, separator: str = "-") -> str:
        """Convert ``value`` into a URL-safe slug.

        Steps: NFKD-normalise -> drop combining marks (accents) -> lowercase
        -> replace non-alphanumeric runs with ``separator`` -> strip edges.
        """
        if not value:
            return ""
        # NFKD decomposition splits accented chars into base + combining mark.
        normalised = unicodedata.normalize("NFKD", value)
        ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
        ascii_only = ascii_only.lower().strip()
        # Replace any run of non-alphanumeric chars with the separator.
        slug = re.sub(r"[^a-z0-9]+", separator, ascii_only)
        # Collapse repeated separators and trim leading/trailing ones.
        slug = re.sub(f"{re.escape(separator)}+", separator, slug)
        return slug.strip(separator)

    # ------------------------------------------------------------------ #
    # Truncation
    # ------------------------------------------------------------------ #
    @staticmethod
    def truncate(value: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate ``value`` to ``max_length`` chars, appending ``suffix``.

        If ``value`` already fits, it is returned unchanged. ``suffix`` length
        is counted within ``max_length`` so the result never exceeds it.
        """
        if not value:
            return ""
        if len(value) <= max_length:
            return value
        if max_length <= len(suffix):
            return suffix[:max_length]
        return value[: max_length - len(suffix)] + suffix

    # ------------------------------------------------------------------ #
    # Case conversion
    # ------------------------------------------------------------------ #
    @staticmethod
    def snake_to_camel(value: str) -> str:
        """Convert ``snake_case`` to ``camelCase``."""
        if not value:
            return ""
        parts = value.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    @staticmethod
    def camel_to_snake(value: str) -> str:
        """Convert ``camelCase`` / ``PascalCase`` to ``snake_case``."""
        if not value:
            return ""
        # Insert "_" before each uppercase letter, then lowercase.
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
        s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    # ------------------------------------------------------------------ #
    # Whitespace
    # ------------------------------------------------------------------ #
    @staticmethod
    def normalise_whitespace(value: Optional[str]) -> str:
        """Collapse internal whitespace runs to a single space and trim edges."""
        if not value:
            return ""
        return re.sub(r"\s+", " ", value).strip()

    # ------------------------------------------------------------------ #
    # Sensitive-data masking
    # ------------------------------------------------------------------ #
    @staticmethod
    def mask_email(value: str) -> str:
        """Mask an email for logs: ``jane.doe@example.com`` -> ``j******e@e******.com``."""
        if not value or "@" not in value:
            return StringHelper.mask(value or "")
        local, domain = value.split("@", 1)
        masked_local = StringHelper._mask_segment(local, reveal=1)
        if "." in domain:
            dname, dsuffix = domain.rsplit(".", 1)
            masked_domain = f"{StringHelper._mask_segment(dname, reveal=1)}.{dsuffix}"
        else:
            masked_domain = StringHelper._mask_segment(domain, reveal=1)
        return f"{masked_local}@{masked_domain}"

    @staticmethod
    def mask(value: str, reveal: int = 0) -> str:
        """Replace all characters with ``*`` (optionally revealing the first ``reveal``)."""
        if not value:
            return ""
        if reveal <= 0:
            return "*" * len(value)
        if reveal >= len(value):
            return value
        return value[:reveal] + "*" * (len(value) - reveal)

    @staticmethod
    def _mask_segment(segment: str, reveal: int = 1) -> str:
        """Mask a single segment, revealing up to ``reveal`` leading chars."""
        if not segment:
            return ""
        if len(segment) <= reveal:
            return segment
        return segment[:reveal] + "*" * (len(segment) - reveal)

    # ------------------------------------------------------------------ #
    # Predicates
    # ------------------------------------------------------------------ #
    @staticmethod
    def is_blank(value: Optional[str]) -> bool:
        """Return ``True`` when ``value`` is ``None`` or whitespace-only."""
        return value is None or not value.strip()

    @staticmethod
    def default_if_blank(
        value: Optional[str], default: str = ""
    ) -> str:
        """Return ``value`` trimmed, or ``default`` when blank."""
        if StringHelper.is_blank(value):
            return default
        return value.strip()  # type: ignore[union-attr]
