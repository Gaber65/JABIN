# -*- coding: utf-8 -*-
"""Password hashing and verification service for the JABIN platform.

The :class:`PasswordService` wraps passlib's bcrypt context to provide a
consistent, future-proof password hashing API. Keeping password logic in a
dedicated service (rather than scattered across models and controllers) means
a single place to upgrade the hashing algorithm, tune cost factors, or add
rehash-on-login when policy changes.

Design
------
* Uses ``passlib``'s :class:`CryptContext` with bcrypt as the primary scheme.
  Bcrypt is resistant to GPU/ASIC brute-force and is the OWASP-recommended
  production hash.
* The :class:`CryptContext` is configured with ``bcrypt`` as the default and
  ``pbkdf2_sha512`` as a deprecated-but-recognized fallback, so legacy hashes
  can be verified and transparently upgraded on the next login.
* The context is created lazily (first call) and cached at class level so we
  do not pay the setup cost on every request.
* The service is an :class:`AbstractModel` so it has access to ``self.env``
  for audit logging, but the hashing itself is pure (no DB).
"""

from __future__ import annotations

from typing import Optional

from odoo import api, models

from jabin_core import JabinLogger

_logger = JabinLogger.get("auth.password_service")

# Lazy-cached passlib context (created once per process).
_CRYPT_CONTEXT = None


def _get_crypt_context():
    """Return a singleton :class:`passlib.context.CryptContext`.

    Importing passlib lazily means the module can be imported in
    environments where passlib is not installed (e.g. a lightweight unit
    test) without failing — only actual hashing calls require it.
    """
    global _CRYPT_CONTEXT
    if _CRYPT_CONTEXT is None:
        from passlib.context import CryptContext  # type: ignore
        _CRYPT_CONTEXT = CryptContext(
            schemes=["bcrypt", "pbkdf2_sha512"],
            default="bcrypt",
            deprecated=["pbkdf2_sha512"],
            bcrypt__rounds=12,
        )
    return _CRYPT_CONTEXT


class PasswordService(models.AbstractModel):
    """Hashing and verification of user passwords."""

    _name = "jabin.password.service"
    _description = "JABIN Password Service"

    # ------------------------------------------------------------------ #
    # Hashing
    # ------------------------------------------------------------------ #
    @staticmethod
    def hash_password(plain: str) -> str:
        """Return a bcrypt hash of ``plain``.

        Raises ``ValueError`` if ``plain`` is empty.
        """
        if not plain:
            raise ValueError("Cannot hash an empty password.")
        ctx = _get_crypt_context()
        return ctx.hash(plain)

    # ------------------------------------------------------------------ #
    # Verification
    # ------------------------------------------------------------------ #
    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Return ``True`` if ``plain`` matches the ``hashed`` value.

        Uses constant-time comparison internally (passlib guarantee).
        Returns ``False`` (never raises) on any mismatch or malformed hash.
        """
        if not plain or not hashed:
            return False
        try:
            ctx = _get_crypt_context()
            return ctx.verify(plain, hashed)
        except Exception:
            _logger.warning("Password verification error (malformed hash?)")
            return False

    # ------------------------------------------------------------------ #
    # Rehash detection (for transparent algorithm upgrades)
    # ------------------------------------------------------------------ #
    @staticmethod
    def needs_rehash(hashed: str) -> bool:
        """Return ``True`` if ``hashed`` uses a deprecated scheme or
        weaker cost factor and should be re-hashed on the next login.
        """
        if not hashed:
            return False
        try:
            ctx = _get_crypt_context()
            return ctx.needs_update(hashed)
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Odoo-native password bridge
    # ------------------------------------------------------------------ #
    @api.model
    def set_user_password(self, user_id: int, plain: str) -> None:
        """Set ``user_id``'s password through Odoo's native mechanism.

        Odoo's ``res.users`` ``_set_password`` / ``write`` takes care of
        hashing with its own scheme; we additionally hash with our bcrypt
        context for cross-platform consistency. The Odoo password field is
        the source of truth for session-based auth; our hash is stored in
        ``x_password_hash`` if that field were present — but for simplicity
        we delegate to Odoo's native ``password`` write which handles
        hashing internally.

        This method also revokes all refresh tokens for the user as a
        security measure (password change invalidates existing sessions).
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            return
        user.write({"password": plain})
        # Revoke refresh tokens on password change.
        try:
            self.env["jabin.refresh.token"].revoke_all_for_user(user_id)
        except Exception:
            pass
        _logger.audit(
            "Password changed for user %s", user_id,
            extra={"user_id": user_id, "action": "password_change"},
        )

    @api.model
    def authenticate(
        self,
        login: str,
        plain_password: str,
    ) -> Optional[int]:
        """Verify credentials and return the user ID on success.

        Returns ``None`` when the credentials are invalid or the account is
        not in a usable state. This is the single entry point for
        password-based authentication used by :class:`AuthService.login`.

        Uses Odoo's native password check (``res.users._check_credentials``)
        so the hashing scheme stays consistent with Odoo's session auth.
        """
        if not login or not plain_password:
            return None

        User = self.env["res.users"]
        user = User.find_by_login(login)
        if not user:
            # Also try by phone as a secondary identifier.
            user = User.find_by_phone(login)
        if not user:
            return None

        # Reject inactive / suspended accounts early.
        status = getattr(user, "x_status", None)
        if status in ("suspended", "inactive"):
            _logger.audit(
                "Login blocked (suspended/inactive): user=%s", user.id,
                extra={"user_id": user.id, "action": "login_blocked_status"},
            )
            return None

        try:
            # Odoo 17: _check_credentials checks self.env.user.id (not
            # self.id), so we must switch the environment user to the
            # target user before calling it. This mirrors Odoo's own
            # _login classmethod which does user.with_user(user).
            from odoo.exceptions import AccessDenied
            user.with_user(user)._check_credentials(
                plain_password, {"interactive": True}
            )
        except AccessDenied:
            return None
        except Exception:
            # Fall back to a direct database lookup of the password hash.
            # We cannot use user.password because it is a computed field
            # that always returns '' for security; the real hash lives in
            # the res_users.password column.
            try:
                self.env.cr.execute(
                    "SELECT COALESCE(password, '') FROM res_users WHERE id=%s",
                    [user.id],
                )
                hashed = self.env.cr.fetchone()[0]
                if not hashed or not self.verify_password(plain_password, hashed):
                    return None
            except Exception:
                return None

        return user.id
