# -*- coding: utf-8 -*-
"""Authentication orchestration service for the JABIN platform.

The :class:`AuthService` is the top-level service that the
:class:`~jabin_auth.controllers.auth_controller.AuthController` delegates to.
It orchestrates :class:`PasswordService`, :class:`TokenService`, and the
audit service to implement the login / logout / refresh / verify / profile
flows.

Why a separate orchestrator?
----------------------------
* Controllers stay thin (parse → delegate → serialise).
* The token and password services are single-responsibility; this service
  composes them into business workflows.
* All audit logging is centralised here so no flow can forget to log.
* The service raises Odoo exceptions (``ValidationError``, ``MissingError``)
  which the ``ExceptionMapper`` translates to HTTP codes — no HTTP knowledge
  leaks into the service.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from odoo import api, fields, models
from odoo.exceptions import MissingError, ValidationError

from jabin_core import (
    EmailValidator,
    JabinLogger,
    PasswordValidator,
    PhoneValidator,
    ValidationHelper,
    ValidationResult,
)
from jabin_security.utils.jwt_utils import JWTError, JWTUtils
from jabin_security.utils.security_context import SecurityContext

_logger = JabinLogger.get("auth.service")

# Fields a user may update on their own profile (self-service).
_PROFILE_UPDATE_FIELDS = {"name", "phone", "avatar"}


class AuthService(models.AbstractModel):
    """Orchestrates authentication flows (login, logout, refresh, profile)."""

    _name = "jabin.auth.service"
    _description = "JABIN Auth Service"

    # ------------------------------------------------------------------ #
    # Login
    # ------------------------------------------------------------------ #
    @api.model
    def login(self, login: str, password: str) -> Dict[str, Any]:
        """Authenticate a user and return a token pair + profile.

        Parameters
        ----------
        login:
            The user's email (or phone, as a secondary identifier).
        password:
            The plain-text password.

        Returns
        -------
        dict
            ``{"user": <public dict>, "tokens": <token pair dict>}``

        Raises
        ------
        ValidationError
            If credentials are missing or invalid.
        """
        if not login or not password:
            raise ValidationError("Login and password are required.")

        # Delegate credential check to the password service.
        user_id = self.env["jabin.password.service"].authenticate(login, password)
        if user_id is None:
            # Audit the failed attempt (without leaking which part failed).
            try:
                self.env["jabin.audit.service"].log_login(
                    user_id=None, success=False, login=login,
                )
            except Exception:
                pass
            raise ValidationError("Invalid login credentials.")

        user = self.env["res.users"].browse(user_id)
        user_type = getattr(user, "x_user_type", None) or "customer"
        email = user.login or ""

        # Issue the token pair.
        tokens = self.env["jabin.token.service"].issue_pair(user_id, user_type, email)

        # Update last-login timestamp.
        try:
            user.sudo().write({"x_last_login": fields.Datetime.now()})
        except Exception:
            pass

        # Audit the successful login.
        try:
            self.env["jabin.audit.service"].log_login(user_id, success=True)
        except Exception:
            pass

        _logger.audit(
            "User logged in: id=%s type=%s", user_id, user_type,
            extra={"user_id": user_id, "action": "login_success"},
        )

        return {
            "user": user.to_public_dict(),
            "tokens": tokens,
        }

    # ------------------------------------------------------------------ #
    # Logout
    # ------------------------------------------------------------------ #
    @api.model
    def logout(self, refresh_token: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Revoke the given refresh token (logout).

        Logout is idempotent: calling it with an already-revoked or invalid
        token succeeds (returns ``logged_out: True``).

        Parameters
        ----------
        refresh_token:
            The refresh token to revoke.
        user_id:
            The authenticated user's ID (from the security context), used
            for audit logging.
        """
        self.env["jabin.token.service"].revoke_refresh_token(refresh_token)

        try:
            self.env["jabin.audit.service"].log_logout(user_id or 0)
        except Exception:
            pass

        return {"logged_out": True}

    # ------------------------------------------------------------------ #
    # Refresh
    # ------------------------------------------------------------------ #
    @api.model
    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """Exchange a refresh token for a new access + refresh pair.

        Raises :class:`JWTError` (mapped to 401) on any failure.
        """
        tokens = self.env["jabin.token.service"].refresh(refresh_token)
        return {"tokens": tokens}

    # ------------------------------------------------------------------ #
    # Verify
    # ------------------------------------------------------------------ #
    @api.model
    def verify(self, access_token: str) -> Dict[str, Any]:
        """Verify an access token and return the decoded identity.

        Returns
        -------
        dict
            ``{"valid": True, "user_id": ..., "user_type": ..., "email": ...}``

        Raises :class:`JWTError` (mapped to 401) if the token is invalid.
        """
        if not access_token:
            raise JWTError("Access token is required.")
        claims = self.env["jabin.token.service"].verify_access_token(access_token)
        return {
            "valid": True,
            "user_id": JWTUtils.get_user_id(claims),
            "user_type": JWTUtils.get_user_type(claims),
            "email": JWTUtils.get_email(claims),
            "expires_at": claims.get("exp"),
        }

    # ------------------------------------------------------------------ #
    # Profile
    # ------------------------------------------------------------------ #
    @api.model
    def get_profile(self, user_id: int) -> Dict[str, Any]:
        """Return the authenticated user's profile (public dict).

        Raises ``MissingError`` if the user does not exist.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError("User not found.")
        return user.to_public_dict()

    @api.model
    def update_profile(
        self,
        user_id: int,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update the authenticated user's own profile (self-service).

        Only a safe subset of fields is accepted (name, phone, avatar).
        Password and email changes go through dedicated flows.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError("User not found.")

        # Whitelist: only allow self-service fields.
        clean = {
            k: v for k, v in payload.items()
            if k in _PROFILE_UPDATE_FIELDS and not ValidationHelper.is_missing(v)
        }

        # Validate phone if present.
        if "phone" in clean:
            vr = PhoneValidator.validate(clean["phone"], field="phone")
            if not vr.ok:
                raise ValidationError("\n".join(e.message for e in vr.errors))
            clean["x_phone"] = PhoneValidator.normalise(clean.pop("phone"))

        # Map remaining fields.
        vals: Dict[str, Any] = {}
        if "name" in clean:
            vals["name"] = clean["name"]
        if "x_phone" in clean:
            vals["x_phone"] = clean["x_phone"]
        if "avatar" in clean:
            vals["x_avatar"] = clean["avatar"]

        if vals:
            user.sudo().write(vals)
            _logger.audit(
                "Profile updated (self): user=%s fields=%s",
                user_id, list(vals.keys()),
                extra={"user_id": user_id, "action": "profile_update"},
            )

        return user.to_public_dict()

    # ------------------------------------------------------------------ #
    # Change password (self-service)
    # ------------------------------------------------------------------ #
    @api.model
    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> Dict[str, Any]:
        """Allow a user to change their own password.

        Requires the current password to be supplied (re-authentication).
        The new password must pass the password policy. All refresh tokens
        are revoked on success (the user must log in again).
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError("User not found.")

        if not current_password or not new_password:
            raise ValidationError("Current password and new password are required.")

        # Verify the current password.
        verified = self.env["jabin.password.service"].authenticate(
            user.login, current_password
        )
        if verified is None:
            raise ValidationError("Current password is incorrect.")

        # Validate the new password against the policy.
        vr = PasswordValidator.validate(new_password, field="new_password")
        if not vr.ok:
            raise ValidationError("\n".join(e.message for e in vr.errors))

        # Set the new password (this also revokes refresh tokens).
        self.env["jabin.password.service"].set_user_password(user_id, new_password)

        return {"password_changed": True}
