# -*- coding: utf-8 -*-
"""Datetime helper for the JABIN platform.

Centralises timezone-aware datetime operations so that every module works with
UTC internally and converts to the client's timezone only at the edges (API
response rendering, report generation).

Why UTC-internal?
-----------------
Storing / comparing naive datetimes across timezones is a classic source of
subtle bugs. By convention the JABIN platform:

* Stores every timestamp in UTC.
* Serialises timestamps as ISO-8601 with an explicit offset (``+00:00``).
* Converts to a requested timezone only when presenting to a user.

All methods are static and free of Odoo dependencies, so they can be used in
workers, tests, and controllers alike.

Extensibility
-------------
* When JWT auth lands, ``now()`` results can be embedded in token claims.
* When business modules need "end of fiscal year" logic, add dedicated helpers
  here rather than scattering date arithmetic across services.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional, Union

# Canonical platform timezone. Centralised so it can be swapped (e.g. via env)
# in one place.
DEFAULT_TZ: str = "UTC"


class DatetimeHelper:
    """Timezone-aware datetime utilities (UTC-internal convention)."""

    # ------------------------------------------------------------------ #
    # "Now" helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def now() -> _dt.datetime:
        """Return the current UTC datetime (timezone-aware)."""
        return _dt.datetime.now(tz=_dt.timezone.utc)

    @staticmethod
    def today() -> _dt.date:
        """Return today's date in UTC."""
        return DatetimeHelper.now().date()

    @staticmethod
    def utcnow_naive() -> _dt.datetime:
        """Return the current UTC datetime **without** tzinfo.

        Some Odoo fields (``fields.Datetime``) historically store naive UTC
        values; this helper bridges the gap when writing to such fields.
        """
        return _dt.datetime.utcnow()

    # ------------------------------------------------------------------ #
    # Parsing / formatting
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_iso(value: str) -> _dt.datetime:
        """Parse an ISO-8601 string into a timezone-aware datetime.

        If the input is naive, it is assumed to be UTC and stamped accordingly.
        """
        parsed = _dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        return parsed

    @staticmethod
    def to_iso(value: _dt.datetime) -> str:
        """Serialise a datetime to an ISO-8601 string.

        Naive datetimes are assumed to be UTC.
        """
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value.isoformat()

    # ------------------------------------------------------------------ #
    # Timezone conversion
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_utc(value: _dt.datetime) -> _dt.datetime:
        """Convert a timezone-aware datetime to UTC.

        Naive datetimes are assumed to already be UTC.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=_dt.timezone.utc)
        return value.astimezone(_dt.timezone.utc)

    @staticmethod
    def to_timezone(value: _dt.datetime, tz_name: str) -> _dt.datetime:
        """Convert a datetime to the named timezone.

        Uses :mod:`zoneinfo` (Python 3.9+ stdlib) to avoid the external
        ``pytz`` dependency. Raises ``ZoneInfoNotFoundError`` for unknown zones.
        """
        from zoneinfo import ZoneInfo  # local import: stdlib in 3.9+

        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value.astimezone(ZoneInfo(tz_name))

    # ------------------------------------------------------------------ #
    # Common date math
    # ------------------------------------------------------------------ #
    @staticmethod
    def add_seconds(value: _dt.datetime, seconds: int) -> _dt.datetime:
        return value + _dt.timedelta(seconds=seconds)

    @staticmethod
    def add_minutes(value: _dt.datetime, minutes: int) -> _dt.datetime:
        return value + _dt.timedelta(minutes=minutes)

    @staticmethod
    def add_hours(value: _dt.datetime, hours: int) -> _dt.datetime:
        return value + _dt.timedelta(hours=hours)

    @staticmethod
    def add_days(value: _dt.datetime, days: int) -> _dt.datetime:
        return value + _dt.timedelta(days=days)

    @staticmethod
    def is_expired(
        value: _dt.datetime,
        ttl_seconds: int,
        reference: Optional[_dt.datetime] = None,
    ) -> bool:
        """Return ``True`` if ``value`` is older than ``ttl_seconds``.

        ``reference`` defaults to :meth:`now` (UTC). Useful for JWT / OTP /
        password-reset expiry checks (wired in later sprints).
        """
        reference = reference or DatetimeHelper.now()
        value = DatetimeHelper.to_utc(value)
        reference = DatetimeHelper.to_utc(reference)
        return (reference - value).total_seconds() > ttl_seconds

    # ------------------------------------------------------------------ #
    # Range helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def start_of_day(value: _dt.date) -> _dt.datetime:
        """Return midnight UTC for the given date."""
        return _dt.datetime.combine(
            value, _dt.time.min, tzinfo=_dt.timezone.utc
        )

    @staticmethod
    def end_of_day(value: _dt.date) -> _dt.datetime:
        """Return 23:59:59.999999 UTC for the given date."""
        return _dt.datetime.combine(
            value, _dt.time.max, tzinfo=_dt.timezone.utc
        )

    @staticmethod
    def humanize_delta(
        value: _dt.datetime, reference: Optional[_dt.datetime] = None
    ) -> str:
        """Return a coarse human-readable age string (e.g. ``"3d ago"``).

        Intended for log lines / non-critical UI; not for precise arithmetic.
        """
        reference = reference or DatetimeHelper.now()
        value = DatetimeHelper.to_utc(value)
        reference = DatetimeHelper.to_utc(reference)
        delta = reference - value
        seconds = int(delta.total_seconds())
        if seconds < 0:
            return "in the future"
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
