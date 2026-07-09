# -*- coding: utf-8 -*-
"""Manifest of the ``jabin_api`` module.

Purpose
-------
``jabin_api`` is the **REST API gateway** of the JABIN platform. It provides
the HTTP infrastructure that every future business module will plug its
endpoints into:

* A base controller (:class:`jabin_api.controllers.base.BaseApiController`)
  that enforces the unified JSON response envelope and centralised exception
  handling via :class:`~jabin_core.utils.exception_mapper.ExceptionMapper`.
* API **versioning** rooted at ``/api/v1/``. The version segment is part of the
  URL so the platform can ship ``/api/v2/`` later without breaking v1 clients.
* A discoverable API root (``GET /api/v1/``) that lists available top-level
  resources -- today empty, ready for Sprint 2+.

Why a dedicated module?
-----------------------
Keeping the HTTP layer separate from the domain/core layer is a Clean
Architecture cornerstone: ``jabin_core`` knows nothing about HTTP, while
``jabin_api`` knows nothing about business rules. Business modules added in
later sprints will declare their own controllers that *inherit* the base
controller, guaranteeing a uniform contract.

Dependencies
------------
* ``jabin_core`` -- for the response builder, exception mapper, logger and
  JSON helper.
* ``base``       -- Odoo's base module (controllers depend on the registry).

Extensibility
-------------
* New version roots (``/api/v2/``) are added as new controller modules that
  re-register routes under the new prefix.
* Business endpoints are added by creating controllers that subclass
  :class:`BaseApiController`; they inherit the envelope + error handling for
  free.
"""

{
    "name": "JABIN API",
    "version": "17.0.1.0.0",
    "category": "Services/JABIN",
    "summary": "JABIN ERP - REST API gateway (controllers, versioning, base controller)",
    "description": """
JABIN API
=========

REST API gateway for the JABIN ERP platform.

Provides:
    * Base API controller with unified JSON response envelope
    * Centralised exception handling
    * API versioning rooted at /api/v1/
    * Discoverable API root endpoint

This module contains NO business endpoints (Sprint 1 only).
    """,
    "author": "JABIN Engineering",
    "website": "https://github.com/Gaber65/JABIN",
    "license": "Other proprietary",
    "depends": ["base", "jabin_core"],
    "data": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
