# -*- coding: utf-8 -*-
"""JSON helper for the JABIN platform.

Standard ``json.dumps`` chokes on a few types that are extremely common in an
ERP context:

* ``datetime`` / ``date``        -- not natively serialisable.
* ``Decimal``                    -- serialised as a float by default, which
  loses precision for monetary values (unacceptable for an e-commerce ERP).
* ``enum.Enum``                  -- serialised as ``"<Enum.MEMBER>"`` by default.
* ``uuid.UUID``                  -- not natively serialisable.
* ``set`` / ``frozenset``        -- not natively serialisable.

:class:`JsonHelper` provides a single :meth:`dumps` / :meth:`loads` pair that
handles all of the above consistently, so controllers never have to write a
custom ``default`` function each time.

Design notes
------------
* The custom :class:`_JabinJSONEncoder` is an internal implementation detail;
  callers only interact with :class:`JsonHelper`.
* ``dumps`` defaults to ``ensure_ascii=False`` so Arabic / CJK content renders
  correctly in logs and responses.
* Monetary ``Decimal`` values are serialised as **strings** to preserve
  precision end-to-end (the frontend parses them with ``Decimal`` / ``BigInt``).
"""

from __future__ import annotations

import datetime as _dt
import decimal
import json
import uuid
from enum import Enum
from typing import Any, Optional, Union


class _JabinJSONEncoder(json.JSONEncoder):
    """Internal JSON encoder aware of ERP-specific types."""

    def default(self, o: Any) -> Any:  # noqa: D401 - JSONEncoder API
        # datetime / date / time -> ISO-8601 string.
        if isinstance(o, _dt.datetime):
            return o.isoformat()
        if isinstance(o, _dt.date):
            return o.isoformat()
        if isinstance(o, _dt.time):
            return o.isoformat()
        # Decimal -> string to preserve precision (monetary values).
        if isinstance(o, decimal.Decimal):
            return str(o)
        # Enums -> their value (so str-enums serialise as the raw string).
        if isinstance(o, Enum):
            return o.value
        # UUID -> canonical hex string.
        if isinstance(o, uuid.UUID):
            return str(o)
        # set / frozenset -> list (order not guaranteed; callers sort if needed).
        if isinstance(o, (set, frozenset)):
            return list(o)
        # bytes -> utf-8 string (best effort; fall back to repr).
        if isinstance(o, (bytes, bytearray)):
            try:
                return o.decode("utf-8")
            except UnicodeDecodeError:
                return repr(o)
        return super().default(o)


class JsonHelper:
    """Safe, ERP-aware JSON serialisation utilities.

    All methods are static; the class acts as a namespace.
    """

    @staticmethod
    def dumps(
        obj: Any,
        ensure_ascii: bool = False,
        indent: Optional[int] = None,
        sort_keys: bool = False,
    ) -> str:
        """Serialise ``obj`` to a JSON string.

        Handles ``datetime``, ``date``, ``Decimal``, ``Enum``, ``UUID``,
        ``set`` and ``bytes`` transparently.
        """
        return json.dumps(
            obj,
            cls=_JabinJSONEncoder,
            ensure_ascii=ensure_ascii,
            indent=indent,
            sort_keys=sort_keys,
        )

    @staticmethod
    def loads(raw: Union[str, bytes, bytearray]) -> Any:
        """Parse a JSON document into native Python types.

        Raises ``json.JSONDecodeError`` on invalid input (callers usually let
        the :class:`~jabin_core.utils.exception_mapper.ExceptionMapper` turn
        that into a 400 response).
        """
        return json.loads(raw)

    @staticmethod
    def dumps_pretty(obj: Any) -> str:
        """Serialise with 2-space indentation (for logs / debugging only)."""
        return JsonHelper.dumps(obj, indent=2, sort_keys=True)
