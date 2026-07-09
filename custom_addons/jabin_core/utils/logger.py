# -*- coding: utf-8 -*-
"""Reusable logging utilities for the JABIN platform.

Provides :class:`JabinLogger`, a thin wrapper around Python's ``logging``
module that adds:

* A custom **AUDIT** log level (between WARNING and ERROR) for security- and
  compliance-relevant events (logins, permission changes, data exports, ...).
* Consistent, prefixed log names (``jabin.<module>``) so logs can be filtered
  with a single ``jabin.*`` filter.
* Contextual extras (``request_id``, ``user_id``) without forcing every
  caller to pass them explicitly.
* A singleton-style factory (:meth:`JabinLogger.get`) so the same underlying
  ``logging.Logger`` is reused across modules, avoiding duplicate handlers.

Why a wrapper and not raw ``logging``?
---------------------------------------
* Centralises the AUDIT level definition once.
* Gives a single, well-documented API for the whole codebase.
* Lets us swap the backend (e.g. to structured JSON logging) in one place.

Extensibility
-------------
* To emit structured JSON logs, override :meth:`JabinLogger._format` or attach
  a custom ``logging.Formatter`` in :meth:`_ensure_handler`.
* To ship audit logs to a SIEM, add a dedicated ``logging.Handler`` for the
  ``jabin.audit`` logger.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Custom AUDIT log level.
#
# Standard levels: DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50.
# We place AUDIT at 35 so it sits between WARNING and ERROR: audit events are
# more important than warnings but not necessarily errors.
# ---------------------------------------------------------------------------
AUDIT_LEVEL: int = 35
AUDIT_LEVEL_NAME: str = "AUDIT"


def _register_audit_level() -> None:
    """Register the ``AUDIT`` level with the ``logging`` module (idempotent)."""
    # ``logging.addLevelName`` is idempotent for the same (level, name) pair.
    logging.addLevelName(AUDIT_LEVEL, AUDIT_LEVEL_NAME)

    # Attach a ``logger.audit(message, ...)`` convenience method to Logger so
    # callers can write ``logger.audit("...")`` just like ``logger.info(...)``.
    def _audit(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(AUDIT_LEVEL):
            self._log(AUDIT_LEVEL, msg, args, **kwargs)

    if not hasattr(logging.Logger, "audit"):
        logging.Logger.audit = _audit  # type: ignore[attr-defined]

    # Also on LoggerAdapter for parity.
    if not hasattr(logging.LoggerAdapter, "audit"):

        def _adapter_audit(
            self: logging.LoggerAdapter, msg: str, *args: Any, **kwargs: Any
        ) -> None:
            self.logger.audit(msg, *args, **kwargs)

        logging.LoggerAdapter.audit = _adapter_audit  # type: ignore[attr-defined]


# Register once at import time so every consumer benefits immediately.
_register_audit_level()


class JabinLogger:
    """Factory + thin facade for the platform's loggers.

    Usage
    -----
    ::

        log = JabinLogger.get("orders")
        log.info("Order created", extra={"order_id": 42})
        log.audit("User logged in", extra={"user_id": 7, "ip": "1.2.3.4"})
        log.error("Payment gateway timeout", exc_info=True)

    Design
    ------
    * ``get()`` returns a real :class:`logging.Logger` (or a
      :class:`logging.LoggerAdapter` when context is supplied) so downstream
      code uses the standard logging API.
    * A single :class:`logging.StreamHandler` is attached the first time a
      ``jabin.*`` logger is created, with a formatter that includes the
      timestamp, level, logger name, and message.
    """

    _ROOT_PREFIX: str = "jabin"
    _configured: bool = False

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #
    @classmethod
    def get(
        cls,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        level: Optional[int] = None,
    ) -> Union[logging.Logger, logging.LoggerAdapter]:
        """Return a logger for the given sub-module name.

        Parameters
        ----------
        name:
            Short module name (e.g. ``"orders"``). It is prefixed with
            ``jabin.`` to produce ``jabin.orders``.
        context:
            Optional dict merged into every log record via a
            :class:`logging.LoggerAdapter`. Useful for ``request_id`` /
            ``user_id`` correlation.
        level:
            Optional explicit level; otherwise inherits from the root
            ``jabin`` logger (default ``INFO``).
        """
        # Strip an accidental leading "jabin." to avoid "jabin.jabin.orders".
        clean_name = name.removeprefix(f"{cls._ROOT_PREFIX}.").strip(".")
        full_name = f"{cls._ROOT_PREFIX}.{clean_name}" if clean_name else cls._ROOT_PREFIX

        cls._ensure_configured()

        logger = logging.getLogger(full_name)
        if level is not None:
            logger.setLevel(level)

        if context:
            return cls._wrap(logger, context)
        return logger

    # ------------------------------------------------------------------ #
    # Context helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _wrap(
        logger: logging.Logger, context: Dict[str, Any]
    ) -> logging.LoggerAdapter:
        """Wrap ``logger`` in an adapter that injects ``context`` into records."""
        return logging.LoggerAdapter(logger, context)

    # ------------------------------------------------------------------ #
    # One-time configuration of the ``jabin`` root logger
    # ------------------------------------------------------------------ #
    @classmethod
    def _ensure_configured(cls) -> None:
        """Attach a single stream handler + formatter to the ``jabin`` root.

        Idempotent: safe to call from every ``get()`` invocation.
        """
        if cls._configured:
            return

        root = logging.getLogger(cls._ROOT_PREFIX)
        # Avoid adding duplicate handlers if something already configured it.
        if not root.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    fmt=(
                        "%(asctime)s | %(levelname)-7s | %(name)s | "
                        "%(message)s"
                    ),
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            root.addHandler(handler)
        if root.level == logging.NOTSET:
            root.setLevel(logging.INFO)

        # Prevent propagation so JABIN logs are not duplicated by the root
        # logger's own handlers (e.g. Odoo's).
        root.propagate = False

        cls._configured = True

    # ------------------------------------------------------------------ #
    # Level constants (re-exported for convenience / documentation)
    # ------------------------------------------------------------------ #
    DEBUG: int = logging.DEBUG
    INFO: int = logging.INFO
    WARNING: int = logging.WARNING
    AUDIT: int = AUDIT_LEVEL
    ERROR: int = logging.ERROR
    CRITICAL: int = logging.CRITICAL
