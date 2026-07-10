# -*- coding: utf-8 -*-
"""Services sub-package of ``jabin_users``.

Re-exports the service classes so controllers (and other modules) can import
them in one line::

    from odoo.addons.jabin_users.services import UserService, AddressService
"""

from .user_service import UserService  # noqa: F401
from .address_service import AddressService  # noqa: F401
