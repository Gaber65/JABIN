# -*- coding: utf-8 -*-
"""Refresh-token registry model for the JABIN platform.

The :class:`JabinRefreshToken` model stores metadata about every issued
refresh token so that the platform can:

* **Revoke** a refresh token (logout, password change, admin force-logout).
* **Detect reuse** – if a refresh token is presented after it has been
  revoked, the platform can flag the session as compromised and revoke the
  entire token family.
* **Expire** tokens that have passed their natural lifetime.

This is the persistence layer that backs :class:`TokenService`; controllers
and other services never create rows directly.

Design
------
* Each row stores the ``jti`` (JWT ID) of the refresh token, the user it
  belongs to, the expiry timestamp, and a boolean ``is_revoked`` flag.
* The table is indexed on ``jti`` (fast lookup during refresh) and
  ``user_id`` (fast enumeration for force-logout).
* A token is considered valid only when:
  ``is_revoked == False`` **and** ``expires_at > now()``.
* The model does **not** store the token string itself – only the ``jti``
  and metadata. The actual JWT is stateless; this table is the revocation
  overlay.
"""

from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from jabin_core import JabinLogger

_logger = JabinLogger.get("auth.refresh_token")


class JabinRefreshToken(models.Model):
    """Registry of issued refresh tokens (revocation overlay)."""

    _name = "jabin.refresh.token"
    _description = "JABIN Refresh Token"
    _order = "expires_at desc"

    # ------------------------------------------------------------------ #
    # Fields
    # ------------------------------------------------------------------ #
    jti = fields.Char(
        string="Token ID (jti)",
        required=True,
        index=True,
        help="Unique JWT ID of the refresh token (UUID hex).",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
        ondelete="cascade",
        help="The user this refresh token belongs to.",
    )
    expires_at = fields.Datetime(
        string="Expires At",
        required=True,
        index=True,
        help="When the refresh token becomes naturally invalid.",
    )
    is_revoked = fields.Boolean(
        string="Revoked",
        default=False,
        index=True,
        help="True when the token has been explicitly revoked (logout, etc.).",
    )
    revoked_at = fields.Datetime(
        string="Revoked At",
        help="Timestamp of revocation (if any).",
    )
    ip_address = fields.Char(
        string="Issuing IP",
        help="Client IP from which the token was issued (for audit).",
    )
    user_agent = fields.Char(
        string="Issuing User-Agent",
        help="Client User-Agent from which the token was issued.",
    )

    # ------------------------------------------------------------------ #
    # Constraints
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        ("jti_unique", "unique(jti)", "A refresh token with this jti already exists."),
    ]

    # ------------------------------------------------------------------ #
    # Lifecycle helpers
    # ------------------------------------------------------------------ #
    @api.model
    def register(
        self,
        *,
        jti: str,
        user_id: int,
        expires_at,
        ip_address: str = "",
        user_agent: str = "",
    ):
        """Create a new refresh-token registry row.

        Called by :class:`TokenService` after issuing a refresh token.
        """
        if not jti:
            raise ValidationError("Cannot register a refresh token without a jti.")
        return self.create({
            "jti": jti,
            "user_id": user_id,
            "expires_at": expires_at,
            "ip_address": ip_address or None,
            "user_agent": user_agent or None,
        })

    @api.model
    def find_by_jti(self, jti: str):
        """Return the token row matching ``jti`` (or empty recordset)."""
        if not jti:
            return self.env["jabin.refresh.token"]
        return self.search([("jti", "=", jti)], limit=1)

    @api.model
    def is_valid(self, jti: str) -> bool:
        """Return ``True`` if the token ``jti`` is active and not expired."""
        token = self.find_by_jti(jti)
        if not token:
            return False
        if token.is_revoked:
            return False
        # Check natural expiry.
        now = fields.Datetime.now()
        if token.expires_at and token.expires_at <= now:
            return False
        return True

    def revoke(self):
        """Mark one or more token rows as revoked."""
        now = fields.Datetime.now()
        for token in self:
            if not token.is_revoked:
                token.write({"is_revoked": True, "revoked_at": now})
        _logger.audit(
            "Refresh tokens revoked: count=%d", len(self),
            extra={"action": "revoke_refresh_token", "count": len(self)},
        )
        return True

    @api.model
    def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke every active refresh token for ``user_id``.

        Returns the number of tokens revoked. Used for force-logout
        (password change, admin action, security incident).
        """
        tokens = self.search([
            ("user_id", "=", user_id),
            ("is_revoked", "=", False),
        ])
        count = len(tokens)
        if count:
            tokens.revoke()
        return count

    @api.model
    def purge_expired(self) -> int:
        """Delete rows for tokens that have expired AND are revoked.

        This is a maintenance method (call from a cron job). It only
        removes tokens that are both past their expiry and revoked, to
        keep the audit trail for active-or-recently-revoked tokens.
        Returns the number of rows deleted.
        """
        now = fields.Datetime.now()
        expired = self.search([
            ("is_revoked", "=", True),
            ("expires_at", "<", now),
        ])
        count = len(expired)
        if count:
            # Bypass the model's own delete protection if any – there is
            # none on this model, so a plain unlink is fine.
            expired.unlink()
        return count

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        """Return a JSON-safe dict of the token metadata."""
        self.ensure_one()
        return {
            "id": self.id,
            "jti": self.jti,
            "user_id": self.user_id.id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_revoked": self.is_revoked,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "ip_address": self.ip_address or None,
        }
