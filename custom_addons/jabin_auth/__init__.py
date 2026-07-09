# -*- coding: utf-8 -*-
"""Top-level package of the ``jabin_auth`` module.

Import order (Clean Architecture dependency direction):

1. ``models``      – ORM model (refresh-token registry).
2. ``services``    – business-logic services (PasswordService, TokenService,
   AuthService).
3. ``controllers`` – HTTP adapter (AuthController).

The convenience re-exports let downstream modules do::

    from jabin_auth import AuthService
"""

from . import models  # noqa: F401
from . import services  # noqa: F401
from . import controllers  # noqa: F401

from .services.auth_service import AuthService  # noqa: F401
