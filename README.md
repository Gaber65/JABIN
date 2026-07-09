# JABIN ERP — Backend (Sprint 1 + Sprint 2)

Production-ready backend for the **JABIN** e-commerce platform, built on
**Odoo 17** following Enterprise Software Architecture, SOLID, and Clean
Architecture principles.

> **Sprint 1 scope:** Foundation infrastructure (jabin_core + jabin_api).
>
> **Sprint 2 scope:** Authentication & User Management — three new modules:
> `jabin_auth`, `jabin_users`, `jabin_security`. REST APIs for authentication
> (login, logout, refresh, verify, profile, change-password), user CRUD,
> address management, role-based access control (RBAC), JWT integration, and
> audit logging.

---

## Tech Stack

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Framework    | Odoo 17                                      |
| Language     | Python 3.11                                  |
| Database     | PostgreSQL                                   |
| API          | REST / JSON                                  |
| Auth         | JWT (PyJWT 2.13) + bcrypt (passlib 1.7.4)    |
| Frontend     | OWL (later)                                  |

---

## Repository Layout

```
custom_addons/
├── jabin_core/                      # Sprint 1 — Foundation utilities
│   ├── constants/                   # Centralised enums (6 enums)
│   ├── utils/                       # ResponseBuilder, ExceptionMapper, JabinLogger
│   ├── mixins/                      # Timestamp, Audit, Active, SoftDelete
│   ├── helpers/                     # Json, Datetime, Pagination, String, Validation
│   └── validators/                  # Email, Phone, Password, Price, Weight, UUID
│
├── jabin_api/                       # Sprint 1 — REST API gateway
│   └── controllers/
│       ├── base.py                  # BaseApiController (envelope + error handling)
│       └── api_root.py              # GET /api/v1/ discoverable root
│
├── jabin_users/                     # Sprint 2 — User & Address management
│   ├── models/
│   │   ├── res_users.py             # Extends res.users (JabinUser)
│   │   └── jabin_address.py         # jabin.user.address model
│   ├── services/
│   │   ├── user_service.py          # UserService (business logic)
│   │   └── address_service.py       # AddressService (business logic)
│   └── controllers/
│       ├── user_controller.py       # User CRUD endpoints
│       └── address_controller.py    # Address CRUD endpoints
│
├── jabin_security/                  # Sprint 2 — RBAC, JWT utils, audit
│   ├── utils/
│   │   ├── jwt_utils.py             # JWTUtils (encode/decode/verify)
│   │   └── security_context.py      # SecurityContext (request-scoped identity)
│   ├── models/
│   │   ├── jabin_role.py            # jabin.role model
│   │   ├── jabin_permission.py      # jabin.permission model
│   │   ├── jabin_audit_log.py       # jabin.audit.log (immutable)
│   │   └── res_users_security.py    # Extends res.users with role M2M
│   ├── services/
│   │   ├── permission_service.py    # PermissionService (roles & permissions CRUD)
│   │   ├── authorization_service.py # AuthorizationService (RBAC gate)
│   │   └── audit_service.py         # AuditService (audit logging)
│   ├── decorators/
│   │   ├── auth_required.py         # @auth_required, @auth_optional
│   │   └── permission_required.py   # @permission_required
│   └── security/
│       ├── jabin_security_security.xml  # Access rights
│       └── jabin_security_data.xml      # Seed data (14 permissions, 4 roles)
│
└── jabin_auth/                      # Sprint 2 — Authentication
    ├── models/
    │   └── jabin_refresh_token.py   # jabin.refresh.token (revocation registry)
    ├── services/
    │   ├── password_service.py      # PasswordService (bcrypt hashing)
    │   ├── token_service.py         # TokenService (issue/verify/rotate)
    │   └── auth_service.py          # AuthService (login/logout/refresh/profile)
    └── controllers/
        └── auth_controller.py       # Auth endpoints
```

---

## Sprint 1 — Foundation Infrastructure

### `jabin_core`

The technical foundation. Contains **no business logic** — only reusable
infrastructure: constants, a unified response builder, a centralised exception
mapper, a reusable logger, Odoo mixins, pure-Python helpers, and validators.

### `jabin_api`

The REST gateway. Provides a `BaseApiController` that enforces the unified JSON
envelope and centralised exception handling, plus a discoverable API root at
`/api/v1/`. All Sprint 2 controllers subclass this base controller.

### Global API Response Format

Every API returns the **same** JSON envelope:

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

The envelope is produced by `ResponseBuilder` (jabin_core). Stack traces are
**never** included in the HTTP body; they are logged via `JabinLogger` by the
`ExceptionMapper`.

### Exception Mapping

| Exception         | Code | Meaning                          |
|-------------------|------|----------------------------------|
| `ValidationError` | 400  | Business validation failure      |
| `UserError`       | 400  | Generic user-facing error        |
| `AccessError`     | 403  | Record-level access denied       |
| `MissingError`    | 404  | Record not found                 |
| `AccessDenied`    | 401  | Authentication failed            |
| `IntegrityError`  | 409  | DB constraint violation          |
| `Exception`       | 500  | Unhandled server error           |

### Constants

All enums are `str`-based (JSON-friendly) with `label`, `all_values()`,
`from_value()`, `has_value()` helpers:

- **UserType** — ADMIN, CUSTOMER, MANAGER, EMPLOYEE, DRIVER
- **OrderStatus** — 9 statuses (PENDING … FAILED)
- **PaymentStatus** — 8 statuses (UNPAID … CANCELLED)
- **DeliveryStatus** — 9 statuses (PENDING … CANCELLED)
- **StockStatus** — 5 statuses (IN_STOCK … DISCONTINUED)
- **NotificationType** — 7 types (ORDER, PAYMENT, DELIVERY, PROMOTION, SYSTEM, ACCOUNT, STOCK)

### Mixins, Helpers, and Validators

Reusable `AbstractModel` mixins (Timestamp, Audit, Active, SoftDelete),
pure-Python helpers (Json, Datetime, Pagination, String, Validation), and
validators (Email, Phone, Password, Price, Weight, UUID) are all documented
in their respective module docstrings. See Sprint 1 commit for full details.

---

## Sprint 2 — Authentication & User Management

### Architecture Overview

Sprint 2 adds three modules with a strict Clean Architecture layering:

```
Controllers (HTTP)  →  Services (business logic)  →  Models (ORM)
       ↑                        ↑                        ↑
  decorators                 uses utils              extends res.users
  (auth_required)          (JWTUtils, SecurityContext)
```

**Key design principles:**

- **Business logic stays in services** — controllers are thin HTTP adapters
  that parse requests, delegate to services, and format responses.
- **Services are `AbstractModel`** — they have access to `self.env` for ORM
  operations but contain no HTTP code.
- **`res.users` extension pattern** — JABIN extends Odoo's native `res.users`
  with `x_`-prefixed custom fields rather than creating a parallel user table.
  This keeps authentication compatible with Odoo's session system while adding
  JABIN-specific profile data.
- **Mass-assignment protection** — every service uses explicit whitelist sets
  for create/update operations.
- **Immutable audit log** — the `jabin.audit.log` model overrides `write()`
  and `unlink()` to raise `UserError`, ensuring audit entries can never be
  modified or deleted.

---

### Module: `jabin_users`

User profiles and delivery addresses. Depends on `jabin_core`.

#### Models

**`res.users` extension (JabinUser):**

| Field                  | Type         | Description                              |
|------------------------|--------------|------------------------------------------|
| `x_user_type`          | Selection    | admin / customer / manager / employee / driver |
| `x_phone`              | Char         | Phone number (E.164)                     |
| `x_avatar`             | Char (URL)   | Avatar image URL                         |
| `x_balance`            | Float        | Wallet balance                           |
| `x_currency_id`        | Many2one     | Wallet currency (res.currency)           |
| `x_status`             | Selection    | active / suspended / pending / inactive  |
| `x_last_login`         | Datetime     | Last successful login timestamp          |
| `x_is_active_account`  | Boolean (computed) | True when status==active and not archived |

Helper methods: `find_by_login()`, `find_by_phone()`, `to_public_dict()`,
`_normalize_vals()`. Create/write overrides emit audit log entries.

**`jabin.user.address` (JabinUserAddress):**

| Field             | Type       | Description                              |
|-------------------|------------|------------------------------------------|
| `user_id`         | Many2one   | Owner (res.users, cascade delete)        |
| `title`           | Char       | Address label (Home, Work, …)            |
| `recipient_name`  | Char       | Who to deliver to                        |
| `x_recipient_phone` | Char     | Recipient phone                          |
| `country_id`      | Many2one   | Country (res.country)                    |
| `city`            | Char       | City                                     |
| `district`        | Char       | District / area                          |
| `street`          | Char       | Street address                           |
| `building`        | Char       | Building name/number                     |
| `floor`           | Char       | Floor                                    |
| `apartment`       | Char       | Apartment                                |
| `latitude`        | Float      | GPS latitude (digits=10,7)               |
| `longitude`       | Float      | GPS longitude (digits=10,7)              |
| `is_default`      | Boolean    | Default address (one per user enforced)  |

`_order = "is_default desc, id desc"`. The `_ensure_single_default()` method
guarantees only one default address per user.

#### Services

**`UserService` (`jabin.user.service`):** `create_user()`, `get_user()`,
`list_users()`, `update_user()`, `archive_user()`, `restore_user()`,
`set_status()`. Uses whitelists `_USER_CREATE_FIELDS` and
`_USER_UPDATE_FIELDS` for mass-assignment protection. Validates email
uniqueness, phone format, and user type.

**`AddressService` (`jabin.address.service`):** `create_address()`,
`get_address()`, `list_addresses()`, `update_address()`, `delete_address()`,
`set_default()`. Whitelist `_ADDRESS_FIELDS`. Validates ownership (users can
only manage their own addresses).

#### Endpoints

| Method | Path                                     | Description            |
|--------|------------------------------------------|------------------------|
| GET    | `/api/v1/users`                          | List users (paginated) |
| POST   | `/api/v1/users`                          | Create user            |
| GET    | `/api/v1/users/<int:user_id>`            | Get user by ID         |
| PUT    | `/api/v1/users/<int:user_id>`            | Update user            |
| DELETE | `/api/v1/users/<int:user_id>`            | Archive (soft delete)  |
| POST   | `/api/v1/users/<int:user_id>/restore`    | Restore archived user  |
| PATCH  | `/api/v1/users/<int:user_id>/status`     | Change user status     |
| GET    | `/api/v1/users/<int:user_id>/addresses`  | List user addresses    |
| POST   | `/api/v1/users/<int:user_id>/addresses`  | Create address         |
| GET    | `/api/v1/addresses/<int:address_id>`     | Get address by ID      |
| PUT    | `/api/v1/addresses/<int:address_id>`     | Update address         |
| DELETE | `/api/v1/addresses/<int:address_id>`     | Delete address         |
| PATCH  | `/api/v1/addresses/<int:address_id>/default` | Set default address |

---

### Module: `jabin_security`

Role-based access control, JWT utilities, request-scoped security context,
and audit logging. Depends on `jabin_core` and `jabin_users`.

#### JWT Utilities (`JWTUtils`)

Stateless JWT helper wrapping PyJWT with JABIN-specific conventions.

**Token claims:**

```json
{
    "sub":  "<user_id>",         // subject = user ID (string)
    "type": "<user_type>",       // UserType value
    "email": "<login>",          // email for convenience
    "jti":  "<uuid4 hex>",       // unique token ID (for revocation)
    "kind": "access|refresh",    // token kind
    "iat":  <epoch>,             // issued-at
    "exp":  <epoch>,             // expiry
    "iss":  "jabin"              // issuer
}
```

**Token types:**

| Type    | TTL     | Purpose                                  |
|---------|---------|------------------------------------------|
| access  | 15 min  | API authorization (sent on every request) |
| refresh | 7 days  | Obtain new access tokens without login   |

**Secret resolution order:** explicit argument → `JABIN_JWT_SECRET` env var →
Odoo config parameter `jabin_jwt_secret` → development default (insecure).

The module is **Odoo-agnostic** at the file level — `odoo` is only imported
lazily inside `_resolve_secret()`, so `JWTUtils` can be unit-tested without a
running Odoo server.

All decoding failures are wrapped in a single `JWTError` exception so callers
catch one type instead of the PyJWT hierarchy.

#### SecurityContext

A lightweight, immutable value object that carries the authenticated user's
identity and resolved permissions through a single HTTP request.

```python
ctx = SecurityContext(
    user_id=10, user_type="customer", email="cust@jabin.test",
    roles=["customer"], permissions={"users.read", "addresses.create"},
)
ctx.has_permission("users.read")       # True
ctx.has_all_permissions(["users.read", "users.delete"])  # False
ctx.is_admin                           # False (admin short-circuits all checks)
```

Stored per-request in Odoo's `request.env.context` under the key
`jabin_security_ctx`. The `set()` / `get()` classmethods handle storage and
retrieval. `get()` returns an anonymous context when no request is active.

**Admin short-circuit:** when `user_type == "admin"`, all permission checks
return `True` without inspecting the permissions set.

#### RBAC Models

**`jabin.role`:**

| Field            | Type      | Description                              |
|------------------|-----------|------------------------------------------|
| `code`           | Char (unique) | Snake_case role code (e.g. `user_manager`) |
| `name`           | Char      | Display name                             |
| `description`    | Text      | Role description                         |
| `sequence`       | Integer   | Sort order                               |
| `is_system`      | Boolean   | System role (cannot be deleted)          |
| `active`         | Boolean   | Active flag                              |
| `permission_ids` | Many2many | Permissions granted by this role         |
| `user_ids`       | Many2many | Users assigned this role (res.users)     |

`unlink()` prevents deletion of system roles. `get_permission_codes()`
returns all permission codes aggregated from the role's permissions.

**`jabin.permission`:**

| Field       | Type      | Description                              |
|-------------|-----------|------------------------------------------|
| `code`      | Char (unique) | `<resource>.<action>` format (e.g. `users.create`) |
| `name`      | Char      | Display name                             |
| `description` | Text    | Permission description                   |
| `resource`  | Char (auto) | Extracted from code (before the dot)     |
| `action`    | Char (auto) | Extracted from code (after the dot)      |
| `is_system` | Boolean   | System permission (cannot be deleted)    |
| `active`    | Boolean   | Active flag                              |
| `role_ids`  | Many2many | Roles that grant this permission         |

`create()` / `write()` auto-split the `code` into `resource` and `action`.
`unlink()` prevents deletion of system permissions.

**`jabin.audit.log` (immutable):**

| Field            | Type       | Description                              |
|------------------|------------|------------------------------------------|
| `action`         | Char       | What happened (e.g. `user_login`)        |
| `severity`       | Selection  | info / warning / error / critical        |
| `user_id`        | Many2one   | Acting user (res.users)                  |
| `target_user_id` | Many2one   | Target user (res.users)                  |
| `ip_address`     | Char       | Request IP                               |
| `user_agent`     | Char       | User agent (truncated to 256 chars)      |
| `endpoint`       | Char       | Request path                             |
| `request_id`     | Char       | Correlation ID                           |
| `details`        | Text       | JSON-encoded additional details          |
| `summary`        | Char       | Human-readable summary                   |
| `create_date`    | Datetime   | When the event occurred (readonly)       |

`write()` and `unlink()` both raise `UserError` — audit entries are
append-only and can never be modified.

**`res.users` security extension:** adds `x_jabin_role_ids` (Many2many to
`jabin.role`). Methods: `get_role_codes()`, `get_permission_codes()`
(aggregates permissions from all assigned roles).

#### Services

**`PermissionService` (`jabin.permission.service`):** role and permission CRUD,
role assignment to users. `create_role()`, `get_role()`, `list_roles()`,
`update_role()`, `list_permissions()`, `assign_role()`, `revoke_role()`,
`get_user_roles()`, `resolve_permissions()`, `resolve_roles()`.

**`AuthorizationService` (`jabin.authorization.service`):** the RBAC gate.
`build_context()` resolves a user's roles and permissions into a
`SecurityContext`. `authorize()` is the combined gate used by the
`@permission_required` decorator — it checks account status and permission
simultaneously, returning `False` (not raising) on negative decisions. Admin
short-circuits all checks. Methods: `build_context()`, `is_account_active()`,
`check_permission()`, `check_any_permission()`, `check_all_permissions()`,
`check_role()`, `authorize()`.

**`AuditService` (`jabin.audit.service`):** audit logging. The `log()` method
auto-extracts request metadata (IP, user-agent, endpoint, request-id) and
serializes details to JSON. Errors are swallowed so logging never breaks a
request. Convenience methods: `log_login()`, `log_logout()`,
`log_token_refresh()`, `log_unauthorized()`, `query()`.

#### Decorators

**`@auth_required`** — validates the JWT Bearer token, verifies it is an
access token, resolves the user, checks account status, builds a
`SecurityContext` via `AuthorizationService`, and stores it for downstream
use. Returns 401 on missing/invalid/expired tokens, 403 on inactive accounts.

**`@auth_optional`** — allows anonymous access; builds a `SecurityContext` if
a valid token is present, otherwise sets an anonymous context.

**`@permission_required(permission, *, any_of=None, all_of=None)`** — RBAC
check. Reads the `SecurityContext` set by `@auth_required`, delegates to
`AuthorizationService.authorize()`. Returns 401 if no context, 403 if
permission denied. Audits unauthorized attempts via `log_unauthorized()`.

#### Seed Data (14 permissions, 4 roles)

**System permissions** (noupdate=1):

| Code                   | Description                    |
|------------------------|--------------------------------|
| `users.create`         | Create users                   |
| `users.read`           | Read users                     |
| `users.update`         | Update users                   |
| `users.delete`         | Archive / delete users         |
| `users.manage_status`  | Change user status             |
| `addresses.create`     | Create addresses               |
| `addresses.read`       | Read addresses                 |
| `addresses.update`     | Update addresses               |
| `addresses.delete`     | Delete addresses               |
| `roles.create`         | Create roles                   |
| `roles.read`           | Read roles                     |
| `roles.update`         | Update roles                   |
| `roles.assign`         | Assign/revoke roles to users   |
| `audit.read`           | Read audit logs                |

**System roles** (permission associations noupdate=0):

| Role code          | Permissions                                          |
|--------------------|------------------------------------------------------|
| `admin`            | All 14 permissions (plus admin short-circuit)        |
| `user_manager`     | users.create, users.read, users.update, users.delete, users.manage_status, addresses.* |
| `security_officer` | roles.create, roles.read, roles.update, roles.assign, audit.read |
| `customer`         | addresses.create, addresses.read, addresses.update, addresses.delete |

---

### Module: `jabin_auth`

Authentication flows: login, logout, token refresh, token verification,
profile management, and password changes. Depends on `jabin_core`,
`jabin_users`, and `jabin_security`.

#### Models

**`jabin.refresh.token`** — a revocation registry that stores refresh token
metadata (not the token string itself). This overlay pattern allows token
revocation without storing raw JWTs.

| Field         | Type       | Description                              |
|---------------|------------|------------------------------------------|
| `jti`         | Char (unique, indexed) | JWT token ID (jti claim)     |
| `user_id`     | Many2one   | Owning user (res.users, cascade delete)  |
| `expires_at`  | Datetime (indexed) | Token expiry timestamp           |
| `is_revoked`  | Boolean (indexed) | Whether the token has been revoked |
| `revoked_at`  | Datetime   | When the token was revoked               |
| `ip_address`  | Char       | IP address of token issuance             |
| `user_agent`  | Char       | User agent of token issuance             |

Methods: `register()` (creates a new token record), `find_by_jti()`,
`is_valid()` (not revoked and not expired), `revoke()`,
`revoke_all_for_user()`, `purge_expired()`, `to_dict()`.

#### Services

**`PasswordService` (`jabin.password.service`):** bcrypt password hashing via
passlib. The `CryptContext` is configured with bcrypt as the primary scheme
(rounds=12) and pbkdf2_sha512 as a deprecated-but-recognized fallback for
transparent algorithm upgrades. Methods: `hash_password()`,
`verify_password()`, `needs_rehash()`, `set_user_password()` (also revokes
refresh tokens), `authenticate()` (login + password → user_id or None).

The `authenticate()` method uses Odoo 17's native `_check_credentials` with
`user.with_user(user)` to correctly check the target user's password (Odoo
17's `_check_credentials` checks `self.env.user.id`, not `self.id`). A
fallback path uses direct SQL to retrieve the password hash from the
`res_users` table (since `res.users.password` is a computed field that always
returns `''` for security).

**`TokenService` (`jabin.token.service`):** JWT token lifecycle management.
`issue_pair()` creates an access + refresh token pair and registers the
refresh token in the database. `verify_access_token()` decodes and validates
an access token. `refresh()` implements **refresh token rotation**: it
verifies the presented refresh token, checks it against the revocation
registry, revokes it, and issues a new pair. **Reuse detection:** if a
revoked refresh token is presented again, all of the user's tokens are
revoked (potential token theft). `revoke_refresh_token()`,
`revoke_all_for_user()`.

**`AuthService` (`jabin.auth.service`):** the orchestrator for auth flows.
`login()` (authenticate → issue tokens → update last_login → audit),
`logout()` (revoke refresh token → audit), `refresh()` (delegate to
TokenService), `verify()` (decode access token → return identity dict),
`get_profile()`, `update_profile()` (whitelist: name, phone, avatar),
`change_password()` (re-authenticate with current password, validate new
password, set password which revokes all refresh tokens).

#### Endpoints

| Method | Path                              | Auth           | Description                |
|--------|-----------------------------------|----------------|----------------------------|
| POST   | `/api/v1/auth/login`              | none           | Login (email + password)   |
| POST   | `/api/v1/auth/logout`             | @auth_required | Logout (revoke refresh)    |
| POST   | `/api/v1/auth/refresh`            | none           | Refresh token rotation     |
| GET    | `/api/v1/auth/verify`             | none (Bearer)  | Verify access token        |
| GET    | `/api/v1/auth/profile`            | @auth_required | Get own profile            |
| PUT    | `/api/v1/auth/profile`            | @auth_required | Update own profile         |
| POST   | `/api/v1/auth/change-password`    | @auth_required | Change password            |

#### Login Request / Response

**Request:**

```json
{
    "email": "admin@jabin.test",
    "password": "Abcd1234!"
}
```

**Response (200):**

```json
{
    "success": true,
    "message": "Login successful",
    "code": 200,
    "data": {
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "token_type": "Bearer",
        "expires_in": 900,
        "user": {
            "id": 1,
            "name": "Admin User",
            "email": "admin@jabin.test",
            "user_type": "admin",
            "status": "active"
        }
    },
    "meta": {},
    "errors": []
}
```

#### Security Design

**Refresh token rotation:** every call to `/api/v1/auth/refresh` revokes the
presented refresh token and issues a brand-new access + refresh pair. This
limits the window of vulnerability if a refresh token is stolen.

**Reuse detection:** if a refresh token that has already been revoked is
presented again, the system revokes **all** tokens for that user. This is a
strong signal of token theft (the legitimate user and an attacker both have
the token).

**Password change revokes sessions:** when a user changes their password,
all existing refresh tokens are revoked, forcing re-authentication on all
devices.

**Account status gate:** the `@auth_required` decorator checks that the
user's account is active (`x_status == "active"` and not archived) before
building the security context. Suspended, pending, or inactive accounts
receive a 403 response.

**Immutable audit trail:** all authentication events (login, logout, token
refresh, unauthorized access attempts, password changes) are recorded in the
append-only `jabin.audit.log` table.

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

Protected endpoints use decorators:

```python
from jabin_security import auth_required, permission_required
from jabin_security.utils.security_context import SecurityContext

class ProtectedController(BaseApiController):

    @http.route("/api/v1/protected", methods=["GET"], type="http", auth="none", csrf=False)
    @auth_required
    @permission_required("users.read")
    def protected(self, **kwargs):
        with self.handle() as ctx:
            identity = SecurityContext.get()
            ctx.set_body(ResponseBuilder.success(data={"user_id": identity.user_id}))
        return ctx.response
```

---

## JWT Configuration

Set the JWT signing secret via one of (in priority order):

1. **Environment variable:** `JABIN_JWT_SECRET=<your-secret>`
2. **Odoo config parameter:** `jabin_jwt_secret` (set via `ir.config_parameter`)
3. **Development default** (insecure — never use in production)

For production, set a strong secret (≥ 32 bytes) via environment variable or
Odoo config parameter before deploying.

---

## Verification

A standalone smoke test (`smoke_test.py`) verifies the pure-Python components
without requiring a running Odoo server:

```bash
python3 smoke_test.py
```

**Result: 177 checks passed, 0 failed.**

Coverage:

- **Sprint 1 (96 checks):** constants, ResponseBuilder, ExceptionMapper,
  JabinLogger, all helpers, all validators.
- **Sprint 2 (81 checks):** JWTUtils (encode/decode/verify/error
  handling/claim extraction/secret resolution), SecurityContext
  (construction/anonymous/permission checks/admin short-circuit/
  serialization), password hashing (bcrypt via passlib, verification, salt
  randomization, rehash detection).

Sprint 2 utility classes (`JWTUtils`, `SecurityContext`) are loaded directly
via `importlib` to bypass Odoo-dependent package `__init__.py` chains,
demonstrating their Odoo-agnostic design. Password hashing is tested via the
same passlib `CryptContext` configuration used by `PasswordService`.

> The Odoo-dependent components (models, services, controllers, decorators)
> require a running Odoo 17 server with PostgreSQL and are verified through
  the compile check (38 Python files) and XML validation (4 XML files).

---

## Architecture Rules Applied

- **SOLID** — single-responsibility classes; open/closed via subclassing.
- **Clean Architecture** — controllers know HTTP, services know business rules,
  models know persistence. Dependencies flow inward.
- **DRY** — no duplicated envelope/error/logging/auth code.
- **Modular** — every concern in its own file/package.
- **Reusable** — everything is importable from `jabin_core` / `jabin_security`.
- **Documented** — every file has a module docstring explaining purpose,
  design, and extensibility.
- **Type hints** throughout.
- **Odoo 17 best practices** — `AbstractModel` mixins, `http.Controller`,
  manifest conventions, `res.users` extension pattern.
- **Security** — JWT with rotation and reuse detection, bcrypt password
  hashing, mass-assignment protection, immutable audit logs, admin
  short-circuit RBAC.

---

## Git History

| Commit   | Sprint | Description                                        |
|----------|--------|----------------------------------------------------|
| c28a6e9  | 1      | Foundation infrastructure (jabin_core + jabin_api) |
| (Sprint 2)| 2     | Authentication & User Management (jabin_auth, jabin_users, jabin_security) |

---

## What's Next (Sprint 3+)

Sprint 2 delivers authentication and user management. Future sprints will add
business modules (products, orders, inventory, payments, deliveries, …) on
top of this foundation, each subclassing `BaseApiController`, using the
`@auth_required` / `@permission_required` decorators, and inheriting the
Sprint 1 mixins.

**Waiting for confirmation before proceeding to Sprint 3.**
