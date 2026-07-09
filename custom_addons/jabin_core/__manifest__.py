# -*- coding: utf-8 -*-
"""Manifest of the ``jabin_core`` foundation module.

Purpose
-------
``jabin_core`` is the **technical foundation** of the entire JABIN ERP backend.
It intentionally contains *no business logic* (no products, no orders, no
customers). It only provides reusable infrastructure that every future business
module will depend on:

* **Constants** -- centralised enums (user types, statuses, notification types).
* **Utils**     -- a unified API ``ResponseBuilder``, an ``ExceptionMapper`` that
  converts Odoo exceptions into the JABIN JSON envelope, and a reusable
  ``JabinLogger`` with INFO/WARNING/ERROR/AUDIT levels.
* **Mixins**    -- Odoo ``AbstractModel`` mixins (Timestamp, Audit, Active,
  Soft-Delete) that future models inherit instead of re-declaring the same
  fields/logic over and over.
* **Helpers**   -- pure-Python helper classes (JSON, Datetime, Pagination,
  Validation, String) used by controllers and services alike.
* **Validators**-- a validation *structure* (Email, Phone, Password, Price,
  Weight, UUID) that future modules wire into their own flows.

Why this module exists
----------------------
Centralising cross-cutting concerns in a single, dependency-free module keeps
the codebase DRY, enforces the SOLID/Clean-Architecture rules described in the
project specification, and guarantees that every API endpoint returns the exact
same JSON envelope.

Extensibility
-------------
* New constants can be appended to the enums without breaking existing values
  (all enums are ``IntEnum``/``str`` based with stable, documented values).
* New mixins can be added under ``mixins/`` and re-exported from the package
  ``__init__``.
* New helpers / validators follow the same single-responsibility pattern and are
  registered in their respective ``__init__.py``.
"""

{
    "name": "JABIN Core",
    "version": "17.0.1.0.0",
    "category": "Services/JABIN",
    "summary": "JABIN ERP - Core foundation (constants, utils, mixins, helpers, validators)",
    "description": """
JABIN Core
==========

Foundation infrastructure for the JABIN ERP platform.

Provides:
    * Centralised constants / enums
    * Unified API response builder
    * Centralised exception mapper
    * Reusable logging utilities (INFO / WARNING / ERROR / AUDIT)
    * Reusable Odoo mixins (Timestamp, Audit, Active, SoftDelete)
    * Pure-Python helpers (JSON, Datetime, Pagination, Validation, String)
    * Validation structure (Email, Phone, Password, Price, Weight, UUID)

This module contains NO business logic.
    """,
    "author": "JABIN Engineering",
    "website": "https://github.com/Gaber65/JABIN",
    "license": "Other proprietary",
    "depends": ["base"],
    # jabin_core ships no data, no views, no security of its own.
    "data": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
