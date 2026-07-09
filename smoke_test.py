# -*- coding: utf-8 -*-
"""Smoke test for the pure-Python parts of the JABIN ERP modules (no Odoo).

This script verifies that the Sprint 1 foundation (jabin_core) and the
Sprint 2 authentication / security utilities behave as specified.  It is NOT
a replacement for the Odoo test suite (which would run inside the server); it
is a fast sanity check that the foundation and the Odoo-agnostic security
primitives are wired correctly.

Sprint 1 coverage
    constants, ResponseBuilder, ExceptionMapper, JabinLogger, all helpers,
    all validators.

Sprint 2 coverage
    JWTUtils (encode/decode/verify/claim extraction),
    SecurityContext (permission / role checking, admin short-circuit),
    PasswordService hashing primitives (bcrypt via passlib).

Sprint 2 strategy
    The ``jabin_security`` and ``jabin_auth`` packages contain Odoo-dependent
    ``__init__.py`` files.  To test the Odoo-agnostic utility classes
    (``JWTUtils``, ``SecurityContext``) and the passlib hashing primitives
    without a running Odoo server, we load the relevant source files directly
    with :mod:`importlib` so the package ``__init__`` chain (which imports
    Odoo models) is never triggered.

Run:  python3 smoke_test.py
"""

import sys
import os
import importlib.util

# Make the module importable without Odoo by adding custom_addons to sys.path.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "custom_addons"))

# --------------------------------------------------------------------------- #
# Sprint 1 imports (jabin_core imports Odoo lazily; pure parts work fine)
# --------------------------------------------------------------------------- #
from jabin_core import (
    ResponseBuilder, ApiError, ExceptionMapper, JabinLogger,
    JsonHelper, DatetimeHelper, PaginationHelper, StringHelper,
    ValidationHelper, ValidationResult,
    EmailValidator, PhoneValidator, PasswordValidator,
    PriceValidator, WeightValidator, UUIDValidator,
)
from jabin_core.constants.user_types import UserType
from jabin_core.constants.order_status import OrderStatus
from jabin_core.constants.payment_status import PaymentStatus
from jabin_core.constants.delivery_status import DeliveryStatus
from jabin_core.constants.stock_status import StockStatus
from jabin_core.constants.notification_types import NotificationType

# --------------------------------------------------------------------------- #
# Sprint 2 direct-file imports (bypass Odoo-dependent package __init__)
# --------------------------------------------------------------------------- #
def _load_module_from_file(module_name: str, file_path: str):
    """Load a Python source file as a standalone module via importlib.

    This avoids triggering package ``__init__.py`` chains that may import
    Odoo-dependent modules.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

_jwt_module = _load_module_from_file(
    "jabin_sprint2_jwt",
    os.path.join(HERE, "custom_addons", "jabin_security", "utils", "jwt_utils.py"),
)
JWTUtils = _jwt_module.JWTUtils
JWTError = _jwt_module.JWTError

_ctx_module = _load_module_from_file(
    "jabin_sprint2_security_context",
    os.path.join(HERE, "custom_addons", "jabin_security", "utils", "security_context.py"),
)
SecurityContext = _ctx_module.SecurityContext

# passlib is imported directly for password-hashing tests (the
# PasswordService class itself lives in an Odoo-dependent file, but the
# CryptContext setup is identical).
from passlib.context import CryptContext

_CRYPT = CryptContext(
    schemes=["bcrypt", "pbkdf2_sha512"],
    default="bcrypt",
    deprecated=["pbkdf2_sha512"],
    bcrypt__rounds=12,
)

# --------------------------------------------------------------------------- #
# Test harness
# --------------------------------------------------------------------------- #
passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")


# =========================================================================== #
# SPRINT 1 TESTS
# =========================================================================== #
print("\n=== Constants ===")
check("UserType.ADMIN == 'admin'", UserType.ADMIN.value == "admin")
check("UserType has 5 members", len(list(UserType)) == 5)
check("UserType.has_value('driver')", UserType.has_value("driver"))
check("not UserType.has_value('robot')", not UserType.has_value("robot"))
check("UserType.from_value('customer') == CUSTOMER",
      UserType.from_value("customer") == UserType.CUSTOMER)
check("UserType.ADMIN.label == 'Administrator'", UserType.ADMIN.label == "Administrator")
check("OrderStatus has 9 members", len(list(OrderStatus)) == 9)
check("PaymentStatus has 8 members", len(list(PaymentStatus)) == 8)
check("DeliveryStatus has 9 members", len(list(DeliveryStatus)) == 9)
check("StockStatus has 5 members", len(list(StockStatus)) == 5)
check("NotificationType has 7 members", len(list(NotificationType)) == 7)

print("\n=== ResponseBuilder (success) ===")
r = ResponseBuilder.success(data={"id": 1})
check("success True", r["success"] is True)
check("code 200", r["code"] == 200)
check("message 'Success'", r["message"] == "Success")
check("data has id", r["data"]["id"] == 1)
check("meta is dict", isinstance(r["meta"], dict))
check("errors empty list", r["errors"] == [])

r2 = ResponseBuilder.created(data={"id": 9})
check("created code 201", r2["code"] == 201)
check("created message 'Created'", r2["message"] == "Created")

print("\n=== ResponseBuilder (validation error) ===")
ve = ResponseBuilder.validation_error(
    [ApiError(field="email", message="Email already exists")]
)
check("success False", ve["success"] is False)
check("code 400", ve["code"] == 400)
check("message 'Validation Error'", ve["message"] == "Validation Error")
check("data is None", ve["data"] is None)
check("one error", len(ve["errors"]) == 1)
check("error field email", ve["errors"][0]["field"] == "email")
check("error message", ve["errors"][0]["message"] == "Email already exists")

print("\n=== ResponseBuilder (error responses) ===")
ue = ResponseBuilder.unauthorized()
check("unauthorized code 401", ue["code"] == 401)
check("unauthorized success False", ue["success"] is False)

fe = ResponseBuilder.forbidden()
check("forbidden code 403", fe["code"] == 403)

nfe = ResponseBuilder.not_found()
check("not_found code 404", nfe["code"] == 404)

print("\n=== ResponseBuilder (server error) ===")
se = ResponseBuilder.server_error()
check("success False", se["success"] is False)
check("code 500", se["code"] == 500)
check("message 'Internal Server Error'", se["message"] == "Internal Server Error")
check("data None", se["data"] is None)
check("errors empty", se["errors"] == [])

print("\n=== ExceptionMapper ===")
from jabin_core.utils.exception_mapper import (
    ValidationError as VE, AccessError as AE, MissingError as ME,
)

env, code = ExceptionMapper.handle(VE("Field 'email': invalid"))
check("ValidationError -> 400", code == 400)
check("ValidationError envelope success False", env["success"] is False)

env2, code2 = ExceptionMapper.handle(ME("not found"))
check("MissingError -> 404", code2 == 404)

env3, code3 = ExceptionMapper.handle(AE("no access"))
check("AccessError -> 403", code3 == 403)

env4, code4 = ExceptionMapper.handle(RuntimeError("boom"))
check("RuntimeError -> 500", code4 == 500)
check("RuntimeError message", env4["message"] == "Internal Server Error")
check("no stack trace in body", "Traceback" not in str(env4))

print("\n=== Logger ===")
log = JabinLogger.get("smoke")
check("logger is Logger", hasattr(log, "info"))
check("audit method exists", hasattr(log, "audit"))
log.info("info message")
log.audit("audit message")
log.warning("warning message")
check("AUDIT level 35", JabinLogger.AUDIT == 35)

print("\n=== JsonHelper ===")
import datetime, decimal
out = JsonHelper.dumps({"d": datetime.datetime(2024,1,1,12,0,0), "m": decimal.Decimal("19.99"), "s": {1,2}})
check("datetime iso in json", "2024-01-01T12:00:00" in out)
check("decimal as string in json", '"19.99"' in out)
check("set as list in json", "1" in out and "2" in out)
parsed = JsonHelper.loads('{"a": 1}')
check("loads works", parsed["a"] == 1)

print("\n=== DatetimeHelper ===")
now = DatetimeHelper.now()
check("now is tz-aware", now.tzinfo is not None)
iso = DatetimeHelper.to_iso(now)
check("to_iso roundtrip", DatetimeHelper.parse_iso(iso) == now)
check("add_days works", (DatetimeHelper.add_days(now, 1) - now).days == 1)
check("is_expired False for now", not DatetimeHelper.is_expired(now, 60))

print("\n=== PaginationHelper ===")
pm = PaginationHelper.build(total_items=134, page=1, per_page=20)
check("total_pages 7", pm.total_pages == 7)
check("has_next True", pm.has_next is True)
check("has_prev False", pm.has_prev is False)
check("per_page clamped", PaginationHelper.build(10, 1, 999).per_page == 100)
off, lim = PaginationHelper.offset_limit(page=3, per_page=20)
check("offset 40", off == 40)
check("limit 20", lim == 20)
md = PaginationHelper.meta_dict(134, 1, 20)
check("meta has pagination", "pagination" in md)

print("\n=== StringHelper ===")
check("slugify", StringHelper.slugify("Hello World!") == "hello-world")
check("slugify accents", StringHelper.slugify("Café résumé") == "cafe-resume")
check("truncate", StringHelper.truncate("abcdefghij", 5) == "ab...")
check("snake_to_camel", StringHelper.snake_to_camel("created_at") == "createdAt")
check("camel_to_snake", StringHelper.camel_to_snake("createdAt") == "created_at")
check("mask", StringHelper.mask("1234567890") == "**********")
check("mask_email", StringHelper.mask_email("jane.doe@example.com").count("*") > 0)
check("is_blank True", StringHelper.is_blank("   ") is True)
check("is_blank False", StringHelper.is_blank("x") is False)

print("\n=== ValidationHelper + ValidationResult ===")
check("is_missing None", ValidationHelper.is_missing(None) is True)
check("is_missing ''", ValidationHelper.is_missing("  ") is True)
check("is_missing []", ValidationHelper.is_missing([]) is True)
check("is_present 0", ValidationHelper.is_present(0) is True)
check("is_int '5'", ValidationHelper.is_int("5") is True)
check("is_int '5.5' False", ValidationHelper.is_int("5.5") is False)
check("to_int bad", ValidationHelper.to_int("abc", 7) == 7)
vr = ValidationResult()
vr.require("email", None)
check("result has errors", vr.has_errors)
check("result not ok", not vr.ok)
check("error field email", vr.errors[0].field == "email")

print("\n=== Validators ===")
check("email valid", EmailValidator.is_valid("user@example.com"))
check("email invalid", not EmailValidator.is_valid("not-an-email"))
check("email normalise", EmailValidator.normalise("  USER@Example.COM  ") == "user@example.com")

check("phone valid", PhoneValidator.is_valid("+1 (234) 567-8900"))
check("phone too short", not PhoneValidator.is_valid("123"))
check("phone normalise", PhoneValidator.normalise("+1 (234) 567-8900") == "+12345678900")

check("password valid", PasswordValidator.is_valid("Abcd1234!"))
check("password too short", not PasswordValidator.is_valid("Ab1!"))
check("password no digit", not PasswordValidator.is_valid("Abcdefg!"))
check("password score", PasswordValidator.strength_score("Abcd1234!") >= 4)

check("price valid", PriceValidator.is_valid("19.99"))
check("price negative invalid", not PriceValidator.is_valid("-5.00"))
check("price too many decimals", not PriceValidator.is_valid("19.999"))
check("price non-numeric", not PriceValidator.is_valid("abc"))

check("weight valid", WeightValidator.is_valid("1.250"))
check("weight negative invalid", not WeightValidator.is_valid("-1"))
check("weight too many decimals", not WeightValidator.is_valid("1.1234"))

check("uuid valid", UUIDValidator.is_valid("550e8300-e29b-41d4-a716-446655440000"))
check("uuid invalid", not UUIDValidator.is_valid("not-a-uuid"))
check("uuid normalise", UUIDValidator.normalise("550E8300E29B41D4A716446655440000") == "550e8300-e29b-41d4-a716-446655440000")
check("uuid generate", len(UUIDValidator.generate()) == 36)


# =========================================================================== #
# SPRINT 2 TESTS
# =========================================================================== #

# Use a fixed test secret so decoding tests are deterministic.
TEST_SECRET = "jabin-smoke-test-secret-key-for-jwt-ops"

print("\n=== JWTUtils: token encoding ===")
access_tok = JWTUtils.encode_access_token(
    user_id=42, user_type="admin", email="admin@jabin.test",
    secret=TEST_SECRET,
)
check("access token is non-empty string", isinstance(access_tok, str) and len(access_tok) > 20)
check("access token has 3 segments", access_tok.count(".") == 2)

refresh_tok = JWTUtils.encode_refresh_token(
    user_id=42, user_type="admin", email="admin@jabin.test",
    secret=TEST_SECRET,
)
check("refresh token is non-empty string", isinstance(refresh_tok, str) and len(refresh_tok) > 20)
check("refresh token differs from access", refresh_tok != access_tok)

print("\n=== JWTUtils: token decoding ===")
claims = JWTUtils.decode_token(access_tok, secret=TEST_SECRET)
check("decoded sub == '42'", claims["sub"] == "42")
check("decoded type == 'admin'", claims["type"] == "admin")
check("decoded email matches", claims["email"] == "admin@jabin.test")
check("decoded issuer == 'jabin'", claims["iss"] == "jabin")
check("decoded kind == 'access'", claims["kind"] == "access")
check("decoded has jti", "jti" in claims and len(claims["jti"]) == 32)
check("decoded has iat", "iat" in claims)
check("decoded has exp", "exp" in claims)
check("exp > iat", claims["exp"] > claims["iat"])

refresh_claims = JWTUtils.decode_token(refresh_tok, secret=TEST_SECRET)
check("refresh kind == 'refresh'", refresh_claims["kind"] == "refresh")
check("refresh exp much later than access",
      refresh_claims["exp"] > claims["exp"] + 3600)

print("\n=== JWTUtils: error handling ===")
# Wrong secret
try:
    JWTUtils.decode_token(access_tok, secret="wrong-secret")
    check("wrong secret raises", False)
except JWTError:
    check("wrong secret raises JWTError", True)
except Exception:
    check("wrong secret raises JWTError", False)

# Empty token
try:
    JWTUtils.decode_token("")
    check("empty token raises", False)
except JWTError:
    check("empty token raises JWTError", True)

# Tampered token
tampered = access_tok[:-4] + "AAAA"
try:
    JWTUtils.decode_token(tampered, secret=TEST_SECRET)
    check("tampered token raises", False)
except JWTError:
    check("tampered token raises JWTError", True)

# Expired token (ttl=0)
expired_tok = JWTUtils.encode_access_token(
    user_id=1, user_type="customer", email="c@jabin.test",
    secret=TEST_SECRET, ttl=0,
)
import time as _time
_time.sleep(1.1)  # ensure it's actually expired
try:
    JWTUtils.decode_token(expired_tok, secret=TEST_SECRET)
    check("expired token raises", False)
except JWTError as exc:
    check("expired token raises JWTError", True)
    check("expired message mentions expired", "expired" in str(exc).lower())

# Expired token with verify_exp=False should still decode
expired_claims = JWTUtils.decode_token(expired_tok, secret=TEST_SECRET, verify_exp=False)
check("expired token decodes with verify_exp=False", expired_claims["sub"] == "1")

print("\n=== JWTUtils: decode without verification ===")
unverified = JWTUtils.decode_without_verification(access_tok)
check("unverified sub == '42'", unverified["sub"] == "42")
check("unverified issuer == 'jabin'", unverified["iss"] == "jabin")

# decode_without_verification should work even with wrong "secret" concept
# (it doesn't verify at all)
unverified2 = JWTUtils.decode_without_verification(refresh_tok)
check("unverified refresh kind == 'refresh'", unverified2["kind"] == "refresh")

print("\n=== JWTUtils: claim extraction helpers ===")
check("get_user_id returns 42", JWTUtils.get_user_id(claims) == 42)
check("get_token_id returns str", isinstance(JWTUtils.get_token_id(claims), str))
check("get_token_kind returns 'access'", JWTUtils.get_token_kind(claims) == "access")
check("get_user_type returns 'admin'", JWTUtils.get_user_type(claims) == "admin")
check("get_email returns email", JWTUtils.get_email(claims) == "admin@jabin.test")
check("get_user_id on bad sub returns None",
      JWTUtils.get_user_id({"sub": "not-a-number"}) is None)
check("get_user_id on missing sub returns None",
      JWTUtils.get_user_id({}) is None)

print("\n=== JWTUtils: secret resolution ===")
# Explicit secret takes priority
tok_explicit = JWTUtils.encode_access_token(
    1, "admin", "a@b.test", secret="explicit-secret-xyz",
)
try:
    JWTUtils.decode_token(tok_explicit, secret="explicit-secret-xyz")
    check("explicit secret works", True)
except JWTError:
    check("explicit secret works", False)

# Environment variable resolution
os.environ["JABIN_JWT_SECRET"] = "env-secret-abc-123"
tok_env = JWTUtils.encode_access_token(1, "admin", "a@b.test")
check("env secret used when no explicit secret",
      JWTUtils.decode_token(tok_env, secret="env-secret-abc-123") is not None)
del os.environ["JABIN_JWT_SECRET"]

print("\n=== SecurityContext: construction ===")
ctx = SecurityContext(
    user_id=10,
    user_type="customer",
    email="cust@jabin.test",
    roles=["customer"],
    permissions={"users.read", "addresses.create"},
    token_id="abc123",
)
check("is_authenticated True", ctx.is_authenticated is True)
check("is_admin False for customer", ctx.is_admin is False)
check("user_id == 10", ctx.user_id == 10)
check("roles list preserved", ctx.roles == ["customer"])
check("permissions set preserved", ctx.permissions == {"users.read", "addresses.create"})

print("\n=== SecurityContext: anonymous ===")
anon = SecurityContext.anonymous()
check("anonymous not authenticated", anon.is_authenticated is False)
check("anonymous user_id is None", anon.user_id is None)
check("anonymous is_admin False", anon.is_admin is False)
check("anonymous no permissions", len(anon.permissions) == 0)
check("anonymous no roles", len(anon.roles) == 0)

print("\n=== SecurityContext: permission checks ===")
check("has_permission users.read", ctx.has_permission("users.read") is True)
check("not has_permission users.delete", ctx.has_permission("users.delete") is False)
check("has_any_permission one match", ctx.has_any_permission(["users.delete", "users.read"]) is True)
check("has_any_permission no match", ctx.has_any_permission(["users.delete", "roles.create"]) is False)
check("has_all_permissions all match", ctx.has_all_permissions(["users.read", "addresses.create"]) is True)
check("has_all_permissions partial match", ctx.has_all_permissions(["users.read", "users.delete"]) is False)
check("has_role customer", ctx.has_role("customer") is True)
check("not has_role admin", ctx.has_role("admin") is False)

print("\n=== SecurityContext: admin short-circuit ===")
admin_ctx = SecurityContext(
    user_id=1,
    user_type="admin",
    email="admin@jabin.test",
    roles=["admin"],
    permissions=set(),  # admin has NO explicit permissions
)
check("admin is_admin True", admin_ctx.is_admin is True)
check("admin has_permission any code (short-circuit)",
      admin_ctx.has_permission("anything.i.want") is True)
check("admin has_any_permission (short-circuit)",
      admin_ctx.has_any_permission(["nonexistent.thing"]) is True)
check("admin has_all_permissions (short-circuit)",
      admin_ctx.has_all_permissions(["x.y", "a.b", "c.d"]) is True)

print("\n=== SecurityContext: serialization ===")
d = ctx.to_dict()
check("to_dict has user_id", d["user_id"] == 10)
check("to_dict has user_type", d["user_type"] == "customer")
check("to_dict has email", d["email"] == "cust@jabin.test")
check("to_dict has roles list", d["roles"] == ["customer"])
check("to_dict has permission_count", d["permission_count"] == 2)
check("to_dict has token_id", d["token_id"] == "abc123")
check("to_dict has is_authenticated", d["is_authenticated"] is True)
check("to_dict has is_admin", d["is_admin"] is False)
# Ensure permissions themselves are NOT leaked (only count)
check("to_dict does not leak permission codes", "permissions" not in d)

print("\n=== SecurityContext: get() without Odoo returns anonymous ===")
retrieved = SecurityContext.get()
check("get() without Odoo request returns anonymous", retrieved.is_authenticated is False)

print("\n=== PasswordService: bcrypt hashing (passlib) ===")
plain = "MySecureP@ssw0rd!"
hashed = _CRYPT.hash(plain)
check("hash is non-empty string", isinstance(hashed, str) and len(hashed) > 20)
check("hash starts with bcrypt identifier", hashed.startswith("$2") or hashed.startswith("$pbkdf2"))

print("\n=== PasswordService: password verification ===")
check("verify correct password", _CRYPT.verify(plain, hashed) is True)
check("verify wrong password", _CRYPT.verify("WrongPassword!", hashed) is False)
check("verify empty plain returns False", _CRYPT.verify("", hashed) is False)

print("\n=== PasswordService: hash determinism / uniqueness ===")
hashed2 = _CRYPT.hash(plain)
check("two hashes differ (salt randomization)", hashed != hashed2)
check("both hashes verify same password",
      _CRYPT.verify(plain, hashed) and _CRYPT.verify(plain, hashed2))

print("\n=== PasswordService: needs_rehash detection ===")
# A fresh bcrypt hash should not need rehash
check("fresh bcrypt does not need rehash", _CRYPT.needs_update(hashed) is False)

# A deprecated pbkdf2_sha512 hash should need rehash
pbkdf2_hash = _CRYPT.hash("legacy-test-password")  # will be bcrypt by default
# Manually create a pbkdf2 hash to test deprecated detection
from passlib.hash import pbkdf2_sha512
legacy = pbkdf2_sha512.hash("old-password")
check("pbkdf2 hash needs rehash", _CRYPT.needs_update(legacy) is True)
check("legacy hash still verifies", _CRYPT.verify("old-password", legacy) is True)

print("\n=== PasswordService: empty password handling ===")
# Passlib's CryptContext itself does NOT reject empty strings — it will
# hash them.  The empty-password guard lives in PasswordService.hash_password()
# (``if not plain: raise ValueError``), which is a service-layer concern
# that cannot be tested here without Odoo.  We verify the passlib behaviour
# so we know the service guard is the actual protection.
try:
    empty_hash = _CRYPT.hash("")
    check("passlib hashes empty string (guard is service-layer)", True)
    check("empty hash verifies", _CRYPT.verify("", empty_hash) is True)
except Exception:
    check("passlib hashes empty string (guard is service-layer)", False)


# =========================================================================== #
# RESULTS
# =========================================================================== #
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'='*60}")
sys.exit(1 if failed else 0)
