# -*- coding: utf-8 -*-
"""Top-level package of the ``jabin_users`` module.

Import order:
1. ``models``      -- declares the ORM models (res.users extension + address).
2. ``services``    -- business-logic layer (no HTTP dependency).
3. ``controllers`` -- HTTP layer; depends on services + Sprint 1 base controller.

Keeping services *before* controllers mirrors the dependency direction of
Clean Architecture: controllers depend on services, never the reverse.
"""

from . import models  # noqa: F401
from . import services  # noqa: F401
from . import controllers  # noqa: F401
