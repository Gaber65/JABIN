# -*- coding: utf-8 -*-
"""Audit log model for the JABIN platform.

The :class:`JabinAuditLog` is an **append-only** record of every
security-relevant event in the system: logins, logouts, permission changes,
sensitive data access, failed authentication attempts, etc.

Design
------
* **Immutable** – the model overrides ``write`` and ``unlink`` to raise,
  preventing any tampering with audit records after creation.
* **Structured** – each entry has an ``action`` code (e.g.
  ``"auth.login"``, ``"user.suspend"``), a severity level, the acting user,
  the target user (when different), an IP address, and a JSON ``details``
  field for extra context.
* **Indexed** – on ``action``, ``user_id``, ``create_date`` for fast querying
  by compliance dashboards.
* **Created via the AuditService** – controllers/services never call
  ``create`` directly; they go through :class:`AuditService.log()` which
  normalises the input and catches errors so a logging failure never breaks
  the request flow.
"""

from __future__ import annotations

import json

from odoo import api, fields, models
from odoo.exceptions import UserError

from jabin_core import JabinLogger

_logger = JabinLogger.get("security.audit_log")


class JabinAuditLog(models.Model):
    """Immutable record of a security-relevant event."""

    _name = "jabin.audit.log"
    _description = "JABIN Audit Log"
    _order = "create_date desc"

    # ------------------------------------------------------------------ #
    # Core fields
    # ------------------------------------------------------------------ #
    action = fields.Char(
        string="Action",
        required=True,
        index=True,
        help="Event code in '<domain>.<event>' format (e.g. 'auth.login').",
    )
    severity = fields.Selection(
        selection=[
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        string="Severity",
        default="info",
        required=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Actor / target
    # ------------------------------------------------------------------ #
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Actor (User)",
        index=True,
        help="The user who performed the action.",
    )
    target_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Target User",
        index=True,
        help="The user the action was performed on (when different from actor).",
    )

    # ------------------------------------------------------------------ #
    # Request metadata
    # ------------------------------------------------------------------ #
    ip_address = fields.Char(
        string="IP Address",
        help="Client IP address (when available).",
    )
    user_agent = fields.Char(
        string="User Agent",
        help="Client User-Agent string (truncated).",
    )
    endpoint = fields.Char(
        string="Endpoint",
        help="API endpoint that triggered the event.",
    )
    request_id = fields.Char(
        string="Request ID",
        index=True,
        help="Correlation ID for the request (when available).",
    )

    # ------------------------------------------------------------------ #
    # Payload
    # ------------------------------------------------------------------ #
    details = fields.Text(
        string="Details (JSON)",
        help="Structured extra context stored as a JSON string.",
    )
    summary = fields.Char(
        string="Summary",
        help="One-line human-readable summary of the event.",
    )

    # ------------------------------------------------------------------ #
    # Timestamp (Odoo provides create_date automatically, but we index it)
    # ------------------------------------------------------------------ #
    create_date = fields.Datetime(
        string="Timestamp",
        readonly=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Immutability
    # ------------------------------------------------------------------ #
    def write(self, vals):
        """Audit logs are immutable once written."""
        raise UserError("Audit log entries cannot be modified.")

    def unlink(self):
        """Audit logs cannot be deleted (compliance requirement)."""
        raise UserError("Audit log entries cannot be deleted.")

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        """Return a JSON-safe dict of the audit entry."""
        self.ensure_one()
        try:
            details = json.loads(self.details) if self.details else None
        except (json.JSONDecodeError, TypeError):
            details = None
        return {
            "id": self.id,
            "action": self.action,
            "severity": self.severity,
            "user_id": self.user_id.id if self.user_id else None,
            "user_name": self.user_id.name if self.user_id else None,
            "target_user_id": self.target_user_id.id if self.target_user_id else None,
            "target_user_name": self.target_user_id.name if self.target_user_id else None,
            "ip_address": self.ip_address or None,
            "endpoint": self.endpoint or None,
            "request_id": self.request_id or None,
            "summary": self.summary or None,
            "details": details,
            "timestamp": self.create_date.isoformat() if self.create_date else None,
        }
