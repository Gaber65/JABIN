# -*- coding: utf-8 -*-
"""Top-level package of the ``jabin_security`` module.

Import order (Clean Architecture dependency direction):

1. ``utils``      -- pure JWT / context helpers (no ORM).  Safe to load first.
2. ``models``     -- ORM models (role, permission, audit log).
3. ``services``   -- business-logic services that use models + utils.
4. ``decorators`` -- HTTP-level decorators that use services + utils.

The convenience re-exports at the bottom let downstream modules
(``jabin_auth``, future business modules) do::

    from jabin_security import auth_required, permission_required, JWTUtils
"""

from . import utils  # noqa: F401
from . import models  # noqa: F401
from . import services  # noqa: F401
from . import decorators  # noqa: F401

# Convenience re-exports
from .utils.jwt_utils import JWTUtils  # noqa: F401
from .utils.security_context import SecurityContext  # noqa: F401
from .decorators.auth_required import auth_required  # noqa: F401
from .decorators.permission_required import permission_required  # noqa: F401
