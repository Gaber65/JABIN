# -*- coding: utf-8 -*-
"""Controllers sub-package of ``jabin_api``.

Import order:
1. ``base``      -- defines :class:`BaseApiController` (no routes of its own).
2. ``api_root``  -- registers the discoverable ``GET /api/v1/`` route and
   depends on the base controller.
"""

from .base import BaseApiController  # noqa: F401
from .api_root import ApiRootController  # noqa: F401
