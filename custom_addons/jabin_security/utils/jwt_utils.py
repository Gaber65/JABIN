# -*- coding: utf-8 -*-
"""JWT encoding / decoding utilities for the JABIN platform.

This module wraps PyJWT with JABIN-specific conventions so that every token
issuer and verifier in the codebase uses the same algorithm, claim structure,
and expiry policy.

Token structure
---------------
Every JABIN JWT contains the following claims::

    {
        "sub":   "<user_id>",          # subject = user ID (string)
        "type":  "user_type",          # UserType value (admin/customer/...)
        "email": "<login>",            # email for convenience
        "jti":   "<uuid4 hex>",        # unique token ID (for revocation)
        "iat":   <epoch>,              # issued-at
        "exp":   <epoch>,              # expiry
        "iss":   "jabin",              # issuer
    }

Access vs refresh tokens
------------------------
``JWTUtils`` produces both short-lived access tokens and long-lived refresh
tokens. The two differ only in the ``type`` claim ("access" vs "refresh") and
the TTL; the same secret and algorithm are used for both. The ``jabin_auth``
module stores refresh token metadata in a DB table for revocation.

Design rules
------------
* The module is **Odoo-agnostic**: it does not import ``odoo`` at module level.
  The secret / TTL values are resolved lazily at call time so the class can be
  unit-tested with explicit parameters.
* Secret resolution order: explicit argument -> environment variable
  ``JABIN_JWT_SECRET`` -> Odoo config parameter ``jabin.jwt_secret`` ->
  a development default (clearly marked as insecure).
* All methods are static; the class is a namespace.
* Decoding errors are wrapped in a single ``JWTError`` so callers do not need
  to know the PyJWT exception hierarchy.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

import jwt

# --------------------------------------------------------------------------- #
# Configuration constants
# --------------------------------------------------------------------------- #

ALGORITHM: str = "HS256"
ISSUER: str = "jabin"

# Default TTLs (seconds). Access tokens are short-lived for security; refresh
# tokens last longer so users do not have to log in every few minutes.
DEFAULT_ACCESS_TTL: int = 15 * 60          # 15 minutes
DEFAULT_REFRESH_TTL: int = 7 * 24 * 3600   # 7 days

# Insecure development default. NEVER use in production.
_DEV_SECRET: str = "jabin-dev-secret-change-in-production-please"

# Claim names (centralised to avoid typos).
CLAIM_SUBJECT = "sub"
CLAIM_USER_TYPE = "type"
CLAIM_EMAIL = "email"
CLAIM_TOKEN_ID = "jti"
CLAIM_ISSUED_AT = "iat"
CLAIM_EXPIRY = "exp"
CLAIM_ISSUER = "iss"
CLAIM_TOKEN_KIND = "kind"  # "access" or "refresh"


class JWTError(Exception):
    """Unified error for all JWT encoding / decoding failures.

    Wraps PyJWT-specific exceptions so the rest of the codebase catches a
    single type.
    """


class JWTUtils:
    """Stateless JWT helper for the JABIN platform."""

    # ------------------------------------------------------------------ #
    # Secret resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_secret(explicit: Optional[str] = None) -> str:
        """Resolve the signing secret.

        Order: explicit arg -> ``JABIN_JWT_SECRET`` env var -> Odoo config
        parameter -> dev default.
        """
        if explicit:
            return explicit

        env_secret = os.environ.get("JABIN_JWT_SECRET")
        if env_secret:
            return env_secret

        # Try Odoo config (lazy import to stay Odoo-agnostic at module level).
        try:
            from odoo.tools.config import config  # type: ignore
            cfg_secret = config.get("jabin_jwt_secret")
            if cfg_secret:
                return cfg_secret
        except Exception:
            pass

        return _DEV_SECRET

    # ------------------------------------------------------------------ #
    # Encoding
    # ------------------------------------------------------------------ #
    @staticmethod
    def encode_access_token(
        user_id: int,
        user_type: str,
        email: str,
        *,
        secret: Optional[str] = None,
        ttl: int = DEFAULT_ACCESS_TTL,
    ) -> str:
        """Produce a short-lived access token for ``user_id``."""
        return JWTUtils._encode(
            user_id=user_id,
            user_type=user_type,
            email=email,
            kind="access",
            ttl=ttl,
            secret=secret,
        )

    @staticmethod
    def encode_refresh_token(
        user_id: int,
        user_type: str,
        email: str,
        *,
        secret: Optional[str] = None,
        ttl: int = DEFAULT_REFRESH_TTL,
    ) -> str:
        """Produce a long-lived refresh token for ``user_id``."""
        return JWTUtils._encode(
            user_id=user_id,
            user_type=user_type,
            email=email,
            kind="refresh",
            ttl=ttl,
            secret=secret,
        )

    @staticmethod
    def _encode(
        user_id: int,
        user_type: str,
        email: str,
        kind: str,
        ttl: int,
        secret: Optional[str],
    ) -> str:
        """Internal: assemble claims and sign."""
        import time
        now = int(time.time())
        claims = {
            CLAIM_SUBJECT: str(user_id),
            CLAIM_USER_TYPE: user_type,
            CLAIM_EMAIL: email,
            CLAIM_TOKEN_ID: uuid.uuid4().hex,
            CLAIM_TOKEN_KIND: kind,
            CLAIM_ISSUED_AT: now,
            CLAIM_EXPIRY: now + ttl,
            CLAIM_ISSUER: ISSUER,
        }
        try:
            return jwt.encode(
                claims,
                JWTUtils._resolve_secret(secret),
                algorithm=ALGORITHM,
            )
        except Exception as exc:
            raise JWTError(f"Failed to encode JWT: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Decoding
    # ------------------------------------------------------------------ #
    @staticmethod
    def decode_token(
        token: str,
        *,
        secret: Optional[str] = None,
        verify_exp: bool = True,
    ) -> Dict[str, Any]:
        """Decode and verify a JWT.

        Returns the claims dict on success. Raises :class:`JWTError` for any
        failure (expired, invalid signature, malformed, wrong issuer).
        """
        if not token:
            raise JWTError("Token is empty.")

        try:
            payload = jwt.decode(
                token,
                JWTUtils._resolve_secret(secret),
                algorithms=[ALGORITHM],
                issuer=ISSUER,
                options={
                    "verify_exp": verify_exp,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise JWTError("Token has expired.") from exc
        except jwt.InvalidIssuerError as exc:
            raise JWTError("Token issuer is invalid.") from exc
        except jwt.InvalidTokenError as exc:
            raise JWTError(f"Invalid token: {exc}") from exc
        except Exception as exc:
            raise JWTError(f"Failed to decode JWT: {exc}") from exc

        return payload

    @staticmethod
    def decode_without_verification(token: str) -> Dict[str, Any]:
        """Decode a token *without* signature / expiry verification.

        Used only for extracting the user ID from an expired token during
        refresh flows. Never use this for authorization decisions.
        """
        if not token:
            raise JWTError("Token is empty.")
        try:
            return jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_iss": False,
                },
                algorithms=[ALGORITHM],
            )
        except Exception as exc:
            raise JWTError(f"Failed to decode JWT (unverified): {exc}") from exc

    # ------------------------------------------------------------------ #
    # Claim extraction helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_user_id(claims: Dict[str, Any]) -> Optional[int]:
        """Extract the user ID from decoded claims."""
        sub = claims.get(CLAIM_SUBJECT)
        if sub is None:
            return None
        try:
            return int(sub)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def get_token_id(claims: Dict[str, Any]) -> Optional[str]:
        """Extract the ``jti`` (token ID) from decoded claims."""
        return claims.get(CLAIM_TOKEN_ID)

    @staticmethod
    def get_token_kind(claims: Dict[str, Any]) -> Optional[str]:
        """Extract the token kind ('access' or 'refresh')."""
        return claims.get(CLAIM_TOKEN_KIND)

    @staticmethod
    def get_user_type(claims: Dict[str, Any]) -> Optional[str]:
        """Extract the user type from decoded claims."""
        return claims.get(CLAIM_USER_TYPE)

    @staticmethod
    def get_email(claims: Dict[str, Any]) -> Optional[str]:
        """Extract the email from decoded claims."""
        return claims.get(CLAIM_EMAIL)
