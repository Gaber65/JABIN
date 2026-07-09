# -*- coding: utf-8 -*-
"""Smoke test for the pure-Python parts of jabin_core (no Odoo required).

This script verifies that the constants, response builder, exception mapper,
logger, helpers and validators behave as specified. It is NOT a replacement
for the Odoo test suite (which would run inside the server); it is a fast
sanity check that the Sprint 1 foundation is wired correctly.

Run:  python3 smoke_test.py
"""

import sys
import os

# Make the module importable without Odoo by adding custom_addons to sys.path.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "custom_addons"))

# jabin_core imports Odoo lazily; the utils/helpers/validators/constants are
# pure Python and import fine. The mixins fall back to stubs when Odoo is
# absent, which is acceptable for this smoke test.
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

print("\n=== ResponseBuilder (server error) ===")
se = ResponseBuilder.server_error()
check("success False", se["success"] is False)
check("code 500", se["code"] == 500)
check("message 'Internal Server Error'", se["message"] == "Internal Server Error")
check("data None", se["data"] is None)
check("errors empty", se["errors"] == [])

print("\n=== ExceptionMapper ===")
# Use the mapper's own exception classes (real Odoo when available, fallbacks
# otherwise) so the test runs in a plain-Python environment too.
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

print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'='*50}")
sys.exit(1 if failed else 0)
