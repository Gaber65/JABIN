# -*- coding: utf-8 -*-
"""Top-level package of the ``jabin_core`` foundation module.

Import order is deliberate:

1. ``constants``  -- pure enums, no dependencies, safe to load first.
2. ``utils``      -- the logger is needed by mixins/helpers, so it loads early.
3. ``helpers``    -- pure-Python utilities that may use constants/utils.
4. ``validators`` -- structural validators that rely on helpers.
5. ``mixins``     -- Odoo ``AbstractModel`` classes; these touch the ORM and must
   be imported last so that every helper they might reference is available.

Each sub-package re-exports its public API here so that downstream modules can
simply do::

    from jabin_core import ResponseBuilder, JabinLogger, USER_TYPES

instead of reaching into internal paths.
"""

from . import constants  # noqa: F401  (re-exported below)

# Utils (logger is a dependency for helpers/mixins, so load before them).
from . import utils  # noqa: F401

from . import helpers  # noqa: F401
from . import validators  # noqa: F401

# Mixins touch the Odoo ORM; import them last.
from . import mixins  # noqa: F401

# ---------------------------------------------------------------------------
# Convenience re-exports for the most commonly used symbols.
# Downstream modules can do ``from jabin_core import ResponseBuilder``.
# ---------------------------------------------------------------------------
from .constants.user_types import UserType  # noqa: F401
from .constants.order_status import OrderStatus  # noqa: F401
from .constants.payment_status import PaymentStatus  # noqa: F401
from .constants.delivery_status import DeliveryStatus  # noqa: F401
from .constants.stock_status import StockStatus  # noqa: F401
from .constants.notification_types import NotificationType  # noqa: F401

from .utils.response_builder import ResponseBuilder, ApiError  # noqa: F401
from .utils.exception_mapper import ExceptionMapper  # noqa: F401
from .utils.logger import JabinLogger  # noqa: F401

from .helpers.pagination_helper import PaginationHelper  # noqa: F401
from .helpers.json_helper import JsonHelper  # noqa: F401
from .helpers.datetime_helper import DatetimeHelper  # noqa: F401
from .helpers.string_helper import StringHelper  # noqa: F401
from .helpers.validation_helper import ValidationHelper, ValidationResult  # noqa: F401

from .validators import (  # noqa: F401
    EmailValidator,
    PhoneValidator,
    PasswordValidator,
    PriceValidator,
    WeightValidator,
    UUIDValidator,
)

from .mixins import (  # noqa: F401
    TimestampMixin,
    AuditMixin,
    ActiveMixin,
    SoftDeleteMixin,
)
