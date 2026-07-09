# -*- coding: utf-8 -*-
"""Manifest of the ``jabin_users`` module (Sprint 2).

Purpose
-------
``jabin_users`` is the **user-management domain** of the JABIN platform. It
extends Odoo's ``res.users`` with JABIN-specific business fields (user type,
balance, status, phone, avatar, last login) and introduces a multi-address
model so each user can own several delivery addresses.

Responsibilities
----------------
* Extend ``res.users`` -> the JABIN user profile (no separate auth table; we
  reuse Odoo's user model and its session/password infrastructure).
* Provide the ``jabin.user.address`` model for multiple addresses per user.
* Expose REST endpoints under ``/api/v1/users`` and ``/api/v1/addresses``.
* Keep **business logic in services**, not controllers (Clean Architecture).

Dependencies
------------
* ``jabin_core`` -- mixins, constants (UserType), validators, response builder.
* ``base``       -- ``res.users`` / ``res.partner``.

What this module does NOT do
----------------------------
* Authentication (login/logout/tokens) -> ``jabin_auth``.
* RBAC / permissions / audit log      -> ``jabin_security``.
* Password hashing / JWT              -> ``jabin_auth`` / ``jabin_security``.

``jabin_users`` only *stores* the password hash on ``res.users`` (Odoo's native
field) and the user-type metadata; the *act* of authenticating is delegated
upward.
"""

{
    "name": "JABIN Users",
    "version": "17.0.1.0.0",
    "category": "Services/JABIN",
    "summary": "JABIN ERP - User profiles, user types, and multi-address management",
    "description": """
JABIN Users
===========

User-management domain for the JABIN ERP platform.

Provides:
    * Extended res.users with JABIN business fields (user type, balance,
      status, phone, avatar, last login).
    * Multi-address model (jabin.user.address).
    * REST APIs under /api/v1/users and /api/v1/addresses.
    * Service layer keeping business logic out of controllers.

User types: Admin, Customer, Manager, Employee, Driver.
    """,
    "author": "JABIN Engineering",
    "website": "https://github.com/Gaber65/JABIN",
    "license": "Other proprietary",
    "depends": ["base", "jabin_core"],
    "data": [
        # Security (access rights) must load before views/data in Odoo.
        "security/jabin_users_security.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
