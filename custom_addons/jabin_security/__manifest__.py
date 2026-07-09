# -*- coding: utf-8 -*-
"""Manifest of the ``jabin_security`` module (Sprint 2).

Purpose
-------
``jabin_security`` is the **security infrastructure** of the JABIN platform.
It provides:

* JWT token encoding / decoding utilities (:mod:`~jabin_security.utils.jwt_utils`).
* A security context that carries the authenticated user + roles through a
  request (:mod:`~jabin_security.utils.security_context`).
* Role and Permission models for RBAC (``jabin.role``, ``jabin.permission``).
* An immutable audit-log model that records every security-relevant event
  (``jabin.audit.log``).
* Services that resolve permissions and make authorization decisions
  (:class:`PermissionService`, :class:`AuthorizationService`,
  :class:`AuditService`).
* Decorators that guard controllers: :func:`auth_required` (validates the JWT
  and loads the user) and :func:`permission_required` (checks a specific
  permission).

Dependencies
------------
* ``jabin_core``  -- validators, logger, response builder.
* ``jabin_users`` -- the extended ``res.users`` model (user identity source).
* ``base``        -- ``res.groups`` / ``res.users``.
* PyJWT (external) -- JWT encoding/decoding.

What this module does NOT do
----------------------------
* Login / logout / refresh flows -> ``jabin_auth`` (which *uses* this module's
  JWT utils and decorators).
* Password hashing -> ``jabin_auth``.
"""

{
    "name": "JABIN Security",
    "version": "17.0.1.0.0",
    "category": "Services/JABIN",
    "summary": "JABIN ERP - RBAC, JWT utilities, audit logging, and security decorators",
    "description": """
JABIN Security
==============

Security infrastructure for the JABIN ERP platform.

Provides:
    * JWT encoding / decoding utilities (PyJWT-based).
    * Security context for request-scoped user / roles.
    * Role-based access control (jabin.role, jabin.permission).
    * Immutable audit log (jabin.audit.log).
    * Authorization services (PermissionService, AuthorizationService, AuditService).
    * Controller decorators (auth_required, permission_required).
    """,
    "author": "JABIN Engineering",
    "website": "https://github.com/Gaber65/JABIN",
    "license": "Other proprietary",
    "depends": ["base", "jabin_core", "jabin_users"],
    "data": [
        "security/jabin_security_security.xml",
        "security/jabin_security_data.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
