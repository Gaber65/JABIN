# -*- coding: utf-8 -*-
"""Top-level package of the ``jabin_api`` module.

Imports the ``controllers`` sub-package which registers the HTTP routes. The
import is placed here (rather than inside ``controllers/__init__.py`` only) so
that Odoo's module loader discovers the controllers when the module is
installed.
"""

from . import controllers  # noqa: F401
