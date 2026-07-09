# -*- coding: utf-8 -*-
"""Token lifecycle service for the JABIN platform.

The :class:`TokenService` orchestrates the creation, verification, refresh,
and revocation of JABIN JWTs. It is the bridge between the stateless
:class:`~jabin_security.utils.jwt_utils.JWTUtils` and the stateful
``jabin.refresh.token`` registry.

Responsibilities
----------------
* **Issue** an access + refresh token pair for a user (on login).
* **Verify** an access token and return the decoded claims (used by the
  ``auth_required`` decorator indirectly and by the ``verify`` endpoint).
* **Refresh** – validate a refresh token, revoke it, and issue a new pair
  (rotation for security).
* **Revoke** – invalidate a refresh token (logout) or all of a user's
  tokens (force-logout / password change).

Security design
---------------
* **Refresh-token rotation**: every refresh call revokes the presented
  token and issues a brand-new pair. This limits the window of a stolen
  refresh token.
* **Reuse detection**: if a revoked refresh token is presented again, the
  service treats it as a compromise signal and revokes *all* of the user's
  tokens (token-family invalidation).
* The service never returns raw refresh tokens in audit logs — only the
  ``jti``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from jabin_core import JabinLogger
from jabin_security.utils.jwt_utils import (
    DEFAULT_ACCESS_TTL,
    DEFAULT_REFRESH_TTL,
    JWTError,
    JWTUtils,
)

_logger = JabinLogger.get("auth.token_service")


class TokenService(models.AbstractModel):
    """JWT lifecycle management (issue, verify, refresh, revoke)."""

    _name = "jabin.token.service"
    _description = "JABIN Token Service"

    # ------------------------------------------------------------------ #
    # Request-metadata helper (for audit)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _request_meta() -> Dict[str, str]:
        """Extract IP and user-agent from the current Odoo request."""
        meta = {"ip_address": "", "user_agent": ""}
        try:
            from odoo.http import request  # type: ignore
            httprequest = request.httprequest
            forwarded = httprequest.headers.get("X-Forwarded-For")
            meta["ip_address"] = (
                forwarded.split(",")[0].strip() if forwarded
                else (httprequest.remote_addr or "")
            )
            ua = httprequest.headers.get("User-Agent", "")
            meta["user_agent"] = ua[:256]
        except Exception:
            pass
        return meta

    # ------------------------------------------------------------------ #
    # Issuance
    # ------------------------------------------------------------------ #
    @api.model
    def issue_pair(
        self,
        user_id: int,
        user_type: str,
        email: str,
    ) -> Dict[str, Any]:
        """Issue a new access + refresh token pair for ``user_id``.

        Registers the refresh token in the revocation registry.

        Returns a dict::

            {
                "access_token": "<jwt>",
                "refresh_token": "<jwt>",
                "token_type": "Bearer",
                "expires_in": 900,       # access TTL in seconds
                "refresh_expires_in": 604800,
            }
        """
        access_token = JWTUtils.encode_access_token(user_id, user_type, email)
        refresh_token = JWTUtils.encode_refresh_token(user_id, user_type, email)

        # Decode the refresh token to get its jti and expiry for the registry.
        try:
            refresh_claims = JWTUtils.decode_token(refresh_token)
            jti = JWTUtils.get_token_id(refresh_claims)
            exp = refresh_claims.get("exp")
        except JWTError:
            raise ValidationError("Failed to issue refresh token.")

        # Convert epoch to datetime for the registry.
        import datetime as _dt
        if exp:
            expires_at = _dt.datetime.fromtimestamp(
                exp, tz=_dt.timezone.utc
            ).replace(tzinfo=None)
        else:
            expires_at = fields.Datetime.now() + _dt.timedelta(seconds=DEFAULT_REFRESH_TTL)

        meta = self._request_meta()
        self.env["jabin.refresh.token"].register(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
        )

        _logger.audit(
            "Token pair issued: user=%s", user_id,
            extra={"user_id": user_id, "action": "token_issued", "jti": jti},
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": DEFAULT_ACCESS_TTL,
            "refresh_expires_in": DEFAULT_REFRESH_TTL,
        }

    # ------------------------------------------------------------------ #
    # Verification
    # ------------------------------------------------------------------ #
    @api.model
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify an access token.

        Returns the claims dict on success. Raises :class:`JWTError` on
        any failure (expired, bad signature, wrong kind).
        """
        claims = JWTUtils.decode_token(token)
        kind = JWTUtils.get_token_kind(claims)
        if kind != "access":
            raise JWTError("Token is not an access token.")
        return claims

    # ------------------------------------------------------------------ #
    # Refresh (rotation)
    # ------------------------------------------------------------------ #
    @api.model
    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """Exchange a valid refresh token for a new access + refresh pair.

        Flow:
        1. Decode the refresh token (without expiry verification first to
           extract the jti, then with full verification).
        2. Look up the jti in the registry.
        3. If the token is revoked → possible reuse → revoke ALL user tokens
           and refuse.
        4. If the token is expired → refuse.
        5. Revoke the presented refresh token (rotation).
        6. Issue a new pair.

        Raises :class:`JWTError` on any failure.
        """
        if not refresh_token:
            raise JWTError("Refresh token is required.")

        # Full verification (signature + expiry + issuer).
        try:
            claims = JWTUtils.decode_token(refresh_token)
        except JWTError as exc:
            _logger.audit(
                "Refresh failed (invalid token): %s", exc,
                extra={"action": "refresh_invalid"},
            )
            raise

        kind = JWTUtils.get_token_kind(claims)
        if kind != "refresh":
            raise JWTError("Provided token is not a refresh token.")

        jti = JWTUtils.get_token_id(claims)
        user_id = JWTUtils.get_user_id(claims)
        if not jti or user_id is None:
            raise JWTError("Refresh token is missing required claims.")

        # Look up the registry row.
        RefreshToken = self.env["jabin.refresh.token"]
        token_row = RefreshToken.find_by_jti(jti)

        # Reuse detection: token not in registry OR already revoked.
        if not token_row:
            # Token was never registered (forged?) or already purged.
            _logger.audit(
                "Refresh failed (unknown jti): user=%s", user_id,
                extra={"user_id": user_id, "action": "refresh_unknown_jti", "jti": jti},
            )
            # Defensive: revoke all user tokens in case of compromise.
            RefreshToken.revoke_all_for_user(user_id)
            raise JWTError("Refresh token is invalid.")

        if token_row.is_revoked:
            # Reuse of a revoked token → strong compromise signal.
            _logger.audit(
                "Refresh REUSE detected: user=%s jti=%s", user_id, jti,
                extra={"user_id": user_id, "action": "refresh_reuse", "jti": jti},
            )
            RefreshToken.revoke_all_for_user(user_id)
            raise JWTError("Refresh token has been revoked. All sessions terminated for security.")

        # Revoke the presented token (rotation).
        token_row.revoke()

        # Resolve the user to get fresh type/email for the new tokens.
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise JWTError("User no longer exists.")
        user_type = getattr(user, "x_user_type", None) or "customer"
        email = user.login or ""

        # Audit the refresh.
        try:
            self.env["jabin.audit.service"].log_token_refresh(user_id, old_jti=jti)
        except Exception:
            pass

        return self.issue_pair(user_id, user_type, email)

    # ------------------------------------------------------------------ #
    # Revocation
    # ------------------------------------------------------------------ #
    @api.model
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a single refresh token (logout).

        Returns ``True`` on success. If the token is invalid or already
        revoked, returns ``False`` (logout is idempotent).
        """
        if not refresh_token:
            return False
        try:
            claims = JWTUtils.decode_without_verification(refresh_token)
        except JWTError:
            return False
        jti = JWTUtils.get_token_id(claims)
        if not jti:
            return False
        token_row = self.env["jabin.refresh.token"].find_by_jti(jti)
        if not token_row:
            return False
        token_row.revoke()
        return True

    @api.model
    def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke every active refresh token for ``user_id``.

        Returns the count of tokens revoked. Used by password-change and
        admin force-logout flows.
        """
        return self.env["jabin.refresh.token"].revoke_all_for_user(user_id)
