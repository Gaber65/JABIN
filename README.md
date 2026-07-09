# JABIN ERP — Backend Foundation (Sprint 1)

Production-ready backend infrastructure for the **JABIN** e-commerce platform,
built on **Odoo 17** following Enterprise Software Architecture, SOLID, and
Clean Architecture principles.

> **Sprint 1 scope:** Foundation infrastructure **only**.
> No products, orders, customers, inventory, payments, or any business logic
> are implemented yet. This sprint delivers the reusable backbone that every
> future business module will depend on.

---

## Tech Stack

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Framework    | Odoo 17                                      |
| Language     | Python 3.11                                  |
| Database     | PostgreSQL                                   |
| API          | REST / JSON                                  |
| Frontend     | OWL (later)                                  |
| Auth         | JWT (later)                                  |

---

## Repository Layout

```
custom_addons/
├── jabin_core/                      # Foundation utilities (no business logic)
│   ├── __manifest__.py              # Module manifest
│   ├── __init__.py                  # Package init + convenience re-exports
│   │
│   ├── constants/                   # Centralised enums
│   │   ├── __init__.py
│   │   ├── user_types.py            # UserType        (ADMIN, CUSTOMER, MANAGER, EMPLOYEE, DRIVER)
│   │   ├── order_status.py          # OrderStatus      (PENDING ... FAILED)
│   │   ├── payment_status.py        # PaymentStatus    (UNPAID ... CANCELLED)
│   │   ├── delivery_status.py       # DeliveryStatus   (PENDING ... CANCELLED)
│   │   ├── stock_status.py          # StockStatus      (IN_STOCK ... DISCONTINUED)
│   │   └── notification_types.py    # NotificationType (ORDER ... STOCK)
│   │
│   ├── utils/                       # Cross-cutting utilities
│   │   ├── __init__.py
│   │   ├── response_builder.py      # ResponseBuilder + ApiError (unified JSON envelope)
│   │   ├── exception_mapper.py      # ExceptionMapper (Odoo exceptions -> envelope)
│   │   └── logger.py                # JabinLogger (INFO / WARNING / ERROR / AUDIT)
│   │
│   ├── mixins/                      # Reusable Odoo AbstractModel mixins
│   │   ├── __init__.py
│   │   ├── timestamp_mixin.py       # create_date / write_date
│   │   ├── audit_mixin.py           # created_by / updated_by
│   │   ├── active_mixin.py          # active flag + archive/unarchive
│   │   └── soft_delete_mixin.py     # is_deleted / deleted_at / deleted_by (prepared)
│   │
│   ├── helpers/                     # Pure-Python helper classes
│   │   ├── __init__.py
│   │   ├── json_helper.py           # JSON (Decimal/datetime/Enum/UUID safe)
│   │   ├── datetime_helper.py       # UTC-internal datetime utilities
│   │   ├── pagination_helper.py     # Pagination meta block builder
│   │   ├── string_helper.py         # slugify / truncate / mask / case conversion
│   │   └── validation_helper.py     # ValidationResult + generic checks
│   │
│   └── validators/                  # Project validation structure
│       ├── __init__.py
│       ├── email_validator.py       # EmailValidator
│       ├── phone_validator.py       # PhoneValidator
│       ├── password_validator.py    # PasswordValidator (policy-based)
│       ├── price_validator.py       # PriceValidator (monetary, Decimal-safe)
│       ├── weight_validator.py      # WeightValidator
│       └── uuid_validator.py        # UUIDValidator
│
└── jabin_api/                       # REST API gateway
    ├── __manifest__.py              # Module manifest (depends on jabin_core)
    ├── __init__.py
    └── controllers/
        ├── __init__.py
        ├── base.py                  # BaseApiController (envelope + error handling)
        └── api_root.py              # GET /api/v1/ discoverable root
```

---

## Modules

### `jabin_core`

The technical foundation. Contains **no business logic** — only reusable
infrastructure: constants, a unified response builder, a centralised exception
mapper, a reusable logger, Odoo mixins, pure-Python helpers, and validators.

### `jabin_api`

The REST gateway. Provides a `BaseApiController` that enforces the unified JSON
envelope and centralised exception handling, plus a discoverable API root at
`/api/v1/`. Business endpoints are added in later sprints by subclassing the
base controller.

---

## Global API Response Format

Every API in the project returns the **same** JSON envelope.

### Success

```json
{
    "success": true,
    "message": "Success",
    "code": 200,
    "data": {},
    "meta": {},
    "errors": []
}
```

### Validation Error

```json
{
    "success": false,
    "message": "Validation Error",
    "code": 400,
    "data": null,
    "errors": [
        { "field": "email", "message": "Email already exists" }
    ]
}
```

### Server Error

```json
{
    "success": false,
    "message": "Internal Server Error",
    "code": 500,
    "data": null,
    "errors": []
}
```

The envelope is produced by `jabin_core.utils.response_builder.ResponseBuilder`.
Stack traces are **never** included in the HTTP body in production; they are
logged via `JabinLogger` by the `ExceptionMapper`.

---

## Global Exception Mapping

`jabin_core.utils.exception_mapper.ExceptionMapper` converts any Odoo / Python
exception raised inside a request into the unified envelope:

| Exception         | Code | Meaning                          |
|-------------------|------|----------------------------------|
| `ValidationError` | 400  | Business validation failure      |
| `UserError`       | 400  | Generic user-facing error        |
| `AccessError`     | 403  | Record-level access denied       |
| `MissingError`    | 404  | Record not found                 |
| `AccessDenied`    | 401  | Authentication failed            |
| `IntegrityError`  | 409  | DB constraint violation          |
| `Exception`       | 500  | Unhandled server error           |

The mapper logs 4xx at WARNING and 5xx at ERROR (with traceback) and always
returns a clean envelope to the client.

---

## Logger

`jabin_core.utils.logger.JabinLogger` adds a custom **AUDIT** level (35,
between WARNING and ERROR) for security/compliance events.

```python
log = JabinLogger.get("orders")
log.info("Order created", extra={"order_id": 42})
log.audit("User logged in", extra={"user_id": 7})
log.error("Payment gateway timeout", exc_info=True)
```

---

## Constants

All enums are `str`-based (JSON-friendly) with stable, documented values and
helper methods (`label`, `all_values()`, `from_value()`, `has_value()`).

- **UserType** — ADMIN, CUSTOMER, MANAGER, EMPLOYEE, DRIVER
- **OrderStatus** — PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, COMPLETED, CANCELLED, RETURNED, FAILED
- **PaymentStatus** — UNPAID, PENDING, PAID, PARTIALLY_PAID, REFUNDED, PARTIALLY_REFUNDED, FAILED, CANCELLED
- **DeliveryStatus** — PENDING, ASSIGNED, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED, RETURNED, CANCELLED
- **StockStatus** — IN_STOCK, LOW_STOCK, OUT_OF_STOCK, BACKORDERED, DISCONTINUED
- **NotificationType** — ORDER, PAYMENT, DELIVERY, PROMOTION, SYSTEM, ACCOUNT, STOCK

---

## Mixins

Reusable Odoo `AbstractModel` mixins that future models inherit:

| Mixin             | Fields / Behaviour                          |
|-------------------|---------------------------------------------|
| `TimestampMixin`  | `create_date`, `write_date` (readonly)      |
| `AuditMixin`      | `created_by`, `updated_by` (auto-stamped)   |
| `ActiveMixin`     | `active` flag + `archive()` / `unarchive()` |
| `SoftDeleteMixin` | `is_deleted`, `deleted_at`, `deleted_by` (prepared) |

Usage:

```python
class MyModel(models.Model):
    _name = "jabin.thing"
    _inherit = [
        "jabin.timestamp.mixin",
        "jabin.audit.mixin",
        "jabin.active.mixin",
        "jabin.soft.delete.mixin",
    ]
```

---

## Helpers

| Helper             | Responsibility                                    |
|--------------------|---------------------------------------------------|
| `JsonHelper`       | Decimal/datetime/Enum/UUID-safe JSON encode/decode|
| `DatetimeHelper`   | UTC-internal datetime parsing & math              |
| `PaginationHelper` | Offset/limit pagination `meta` block              |
| `StringHelper`     | slugify, truncate, mask, case conversion          |
| `ValidationHelper` | `ValidationResult` accumulator + generic checks   |

---

## Validators

| Validator         | Rule                                          |
|-------------------|-----------------------------------------------|
| `EmailValidator`  | RFC-ish format, max 254 chars, normalise       |
| `PhoneValidator`  | E.164-ish, 7–15 digits, normalise             |
| `PasswordValidator`| min 8, upper/lower/digit/special, score 0–5  |
| `PriceValidator`  | non-negative, bounded, ≤2 decimals, Decimal   |
| `WeightValidator` | non-negative, bounded, ≤3 decimals, Decimal   |
| `UUIDValidator`   | canonical UUID parse + normalise              |

Each validator exposes `validate(value) -> ValidationResult`,
`is_valid(value) -> bool`, and (where relevant) `normalise(value)`.

---

## API Versioning

The API is rooted at `/api/v1/`. The version is part of the URL so future
versions (`/api/v2/`) can coexist without breaking existing clients.

`GET /api/v1/` returns platform metadata and an (initially empty) list of
available resources.

---

## How Controllers Use the Foundation

```python
from odoo import http
from jabin_api.controllers.base import BaseApiController
from jabin_core import ResponseBuilder

class ExampleController(BaseApiController):

    @http.route("/api/v1/example", methods=["GET"], type="http", auth="none", csrf=False)
    def example(self, **kwargs):
        with self.handle() as ctx:
            ctx.set_body(ResponseBuilder.success(data={"hello": "world"}))
        return ctx.response
```

The `handle()` context manager catches any exception, maps it to the unified
envelope via `ExceptionMapper`, logs it, and builds a clean `application/json`
response — no stack traces leak to the client.

---

## Verification

A standalone smoke test (`smoke_test.py`) verifies the pure-Python components
without requiring a running Odoo server:

```bash
python3 smoke_test.py
```

Result: **96 checks passed, 0 failed.**

> The Odoo-dependent components (mixins, controllers) are designed to degrade
> gracefully when `odoo` is not importable, falling back to stub classes so the
> pure-Python parts remain unit-testable.

---

## Architecture Rules Applied

- **SOLID** — single-responsibility classes; open/closed via subclassing.
- **Clean Architecture** — `jabin_core` knows nothing about HTTP; `jabin_api`
  knows nothing about business rules.
- **DRY** — no duplicated envelope/error/logging code.
- **Modular** — every concern in its own file/package.
- **Reusable** — everything is importable from `jabin_core`.
- **Documented** — every file has a module docstring explaining purpose,
  design, and extensibility.
- **Type hints** throughout.
- **Odoo 17 best practices** — `AbstractModel` mixins, `http.Controller`,
  manifest conventions.

---

## What's Next (Sprint 2+)

Sprint 1 deliberately stops at infrastructure. Future sprints will add business
modules (users, products, orders, inventory, payments, ...) on top of this
foundation, each subclassing `BaseApiController` and inheriting the mixins.

**Waiting for confirmation before proceeding to Sprint 2.**
