# -*- coding: utf-8 -*-
"""Models sub-package of ``jabin_users``.

Re-exports the ORM models so the module's top-level ``__init__`` can import
them in one line and so that downstream modules can do
``from jabin_users.models import JabinUser``.
"""

from .res_users import JabinUser  # noqa: F401
from .jabin_address import JabinUserAddress  # noqa: F401
