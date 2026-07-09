# -*- coding: utf-8 -*-
"""Manifest of the ``jabin_auth`` module (Sprint 2).

Purpose
-------
``jabin_auth`` is the **authentication gateway** of the JABIN platform. It
wires together the JWT utilities, RBAC infrastructure, and audit logging
provided by ``jabin_security`` into concrete REST endpoints:

* ``POST   /api/v1/auth/login``    – authenticate with email + password,
  receive access + refresh tokens.
* ``POST   /api/v1/auth/logout``   – revoke the current refresh token.
* ``POST   /api/v1/auth/refresh``  – exchange a refresh token for a new
  access token.
* ``GET    /api/v1/auth/verify``   – verify the current access token.
* ``GET    /api/v1/auth/profile``  – get the authenticated user's profile.
* ``PUT    /api/v1/auth/profile``  – update the authenticated user's profile.

Dependencies
------------
* ``jabin_core``     – response builder, exception mapper, logger, validators.
* ``jabin_users``    – the extended ``res.users`` model (identity source).
* ``jabin_security`` – JWT utils, security context, RBAC, audit service,
  decorators.
* ``base``           – ``res.users``, password hashing.
* External: PyJWT, passlib.

Architecture
------------
* **Models**: ``jabin.refresh.token`` – a revocation registry for refresh
  tokens.
* **Services**: ``PasswordService`` (hashing/verification),
  ``TokenService`` (token lifecycle + revocation), ``AuthService``
  (orchestrates login/logout/refresh/profile).
* **Controllers**: ``AuthController`` – thin HTTP adapter delegating to
  ``AuthService``.
"""

{
    "name": "JABIN Auth",
    "version": "17.0.1.0.0",
    "category": "Services/JABIN",
    "summary": "JABIN ERP - Authentication: JWT login, logout, refresh, verify, profile",
    "description": """
JABIN Auth
==========

Authentication gateway for the JABIN ERP platform.

Provides:
    * JWT-based login / logout / refresh / verify endpoints.
    * Authenticated profile retrieval and update.
    * Refresh-token revocation registry.
    * Password hashing and verification (passlib).
    """,
    "author": "JABIN Engineering",
    "website": "https://github.com/Gaber65/JABIN",
    "license": "Other proprietary",
    "depends": ["base", "jabin_core", "jabin_users", "jabin_security"],
    "data": [
        "security/jabin_auth_security.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
