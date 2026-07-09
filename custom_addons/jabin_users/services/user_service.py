# -*- coding: utf-8 -*-
"""User service for the JABIN platform.

The service layer is the **single home of business logic** for the user domain.
Controllers are thin HTTP adapters that parse input, call a service method, and
serialise the result. Every rule that is not HTTP-specific lives here.

Responsibilities
----------------
* **CRUD** – create, read (single + paginated list), update, archive/restore
  users. Wraps the ``JabinUser`` ORM model.
* **Validation** – validates incoming payloads using the Sprint 1 validators
  (Email, Phone, Password) and the ``ValidationResult`` accumulator, so all
  field errors are returned at once.
* **Uniqueness checks** – verifies email / phone uniqueness *before* hitting
  the database constraint, producing a friendly 400 instead of a 409.
* **Audit** – logs security-relevant events (create, update, suspend, restore)
  via ``JabinLogger.audit``.
* **Serialisation** – delegates to ``JabinUser.to_public_dict`` which never
  exposes password hashes.

Design rules
------------
* The service is an :class:`~odoo.models.AbstractModel`` so it can access
  ``self.env`` and participate in Odoo's transaction management. It is never
  exposed to the HTTP layer directly.
* No method raises HTTP-specific exceptions; instead it raises Odoo exceptions
  (``ValidationError``, ``MissingError``, ``AccessError``) which the
  ``ExceptionMapper`` translates into the correct HTTP code.
* Type hints and docstrings on every public method.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from odoo import api, fields, models
from odoo.exceptions import MissingError, ValidationError

from jabin_core import (
    EmailValidator,
    JabinLogger,
    PaginationHelper,
    PasswordValidator,
    PhoneValidator,
    ResponseBuilder,
    ValidationResult,
    ValidationHelper,
)
from jabin_core.constants.user_types import UserType

_logger = JabinLogger.get("users.service")

# Fields a client may send when creating / updating a user. Centralised so the
# service can whitelist input and reject unknown keys (preventing mass-assignment
# attacks on fields like ``x_balance`` or ``x_status``).
_USER_CREATE_FIELDS = {
    "name", "login", "phone", "user_type", "password",
    "status", "avatar",
}
_USER_UPDATE_FIELDS = {
    "name", "phone", "user_type", "status", "avatar",
}


class UserService(models.AbstractModel):
    """Business-logic service for JABIN user accounts."""

    _name = "jabin.user.service"
    _description = "JABIN User Service"

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @api.model
    def _validate_create_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        """Validate the payload for user creation.

        Collects every field-level error into a single ``ValidationResult``
        so the API can return them all at once.
        """
        result = ValidationResult()

        result.require("name", payload.get("name"))
        result.require("email", payload.get("email"))  # 'email' -> login
        result.require("password", payload.get("password"))

        # Email format
        email = payload.get("email")
        if email and not ValidationHelper.is_missing(email):
            result.merge(EmailValidator.validate(email, field="email"))

        # Password policy
        password = payload.get("password")
        if password and not ValidationHelper.is_missing(password):
            result.merge(PasswordValidator.validate(password, field="password"))

        # Phone (optional, but if present must be valid)
        phone = payload.get("phone")
        if phone and not ValidationHelper.is_missing(phone):
            result.merge(PhoneValidator.validate(phone, field="phone"))

        # User type
        user_type = payload.get("user_type")
        if user_type and not ValidationHelper.is_missing(user_type):
            if not UserType.has_value(str(user_type)):
                result.add(
                    f"user_type must be one of {UserType.all_values()}.",
                    field="user_type",
                )

        # Status
        status = payload.get("status")
        if status and not ValidationHelper.is_missing(status):
            valid_statuses = {"active", "suspended", "pending", "inactive"}
            if status not in valid_statuses:
                result.add(
                    f"status must be one of {sorted(valid_statuses)}.",
                    field="status",
                )

        return result

    @api.model
    def _validate_update_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        """Validate the payload for user updates (password not required)."""
        result = ValidationResult()

        email = payload.get("email")
        if email and not ValidationHelper.is_missing(email):
            result.merge(EmailValidator.validate(email, field="email"))

        phone = payload.get("phone")
        if phone and not ValidationHelper.is_missing(phone):
            result.merge(PhoneValidator.validate(phone, field="phone"))

        user_type = payload.get("user_type")
        if user_type and not ValidationHelper.is_missing(user_type):
            if not UserType.has_value(str(user_type)):
                result.add(
                    f"user_type must be one of {UserType.all_values()}.",
                    field="user_type",
                )

        status = payload.get("status")
        if status and not ValidationHelper.is_missing(status):
            valid_statuses = {"active", "suspended", "pending", "inactive"}
            if status not in valid_statuses:
                result.add(
                    f"status must be one of {sorted(valid_statuses)}.",
                    field="status",
                )

        password = payload.get("password")
        if password and not ValidationHelper.is_missing(password):
            result.merge(PasswordValidator.validate(password, field="password"))

        return result

    @api.model
    def _check_uniqueness(
        self,
        email: Optional[str],
        phone: Optional[str],
        exclude_user_id: Optional[int] = None,
    ) -> ValidationResult:
        """Verify email / phone are not already used (friendly 400 vs 409)."""
        result = ValidationResult()
        User = self.env["res.users"]

        if email and not ValidationHelper.is_missing(email):
            existing = User.find_by_login(email)
            if existing and (exclude_user_id is None or existing.id != exclude_user_id):
                result.add("A user with this email already exists.", field="email")

        if phone and not ValidationHelper.is_missing(phone):
            existing = User.find_by_phone(phone)
            if existing and (exclude_user_id is None or existing.id != exclude_user_id):
                result.add("A user with this phone already exists.", field="phone")

        return result

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    @api.model
    def create_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new JABIN user from a validated payload.

        Parameters
        ----------
        payload:
            Dict with keys: name, email, password, phone (opt),
            user_type (opt, default 'customer'), status (opt, default
            'pending').

        Returns
        -------
        dict
            The public serialisation of the created user.

        Raises
        ------
        ValidationError
            If the payload fails validation or uniqueness checks.
        """
        # Whitelist + validate
        clean = self._whitelist(payload, _USER_CREATE_FIELDS)
        vr = self._validate_create_payload(clean)
        vr.merge(self._check_uniqueness(clean.get("email"), clean.get("phone")))
        if not vr.ok:
            raise ValidationError("\n".join(e.message for e in vr.errors))

        # Map API field names -> ORM field names
        vals = self._map_create_vals(clean)
        user = self.env["res.users"].create(vals)
        _logger.audit(
            "User created via service: id=%s email=%s type=%s",
            user.id, user.login, user.x_user_type,
            extra={"user_id": user.id, "action": "create_user"},
        )
        return user.to_public_dict()

    @api.model
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Return the public dict for ``user_id``.

        Raises ``MissingError`` if the user does not exist.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        return user.to_public_dict()

    @api.model
    def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        user_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return a paginated list of users with an optional filter.

        Returns
        -------
        (list, dict)
            The list of public dicts and the ``meta`` pagination block.
        """
        domain: List[Tuple[str, str, Any]] = []
        if user_type:
            domain.append(("x_user_type", "=", user_type))
        if status:
            domain.append(("x_status", "=", status))
        if search:
            domain.append("|")
            domain.append(("name", "ilike", search))
            domain.append(("login", "ilike", search))

        User = self.env["res.users"]
        total = User.search_count(domain)
        meta = PaginationHelper.meta_dict(total, page, per_page)
        offset, limit = PaginationHelper.offset_limit(page, per_page)
        users = User.search(domain, offset=offset, limit=limit, order="id desc")
        return [u.to_public_dict() for u in users], meta

    @api.model
    def update_user(
        self, user_id: int, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing user from a validated payload.

        Password updates are supported but require the full password policy
        to pass. Email changes are allowed but go through uniqueness checks.
        """
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")

        clean = self._whitelist(payload, _USER_UPDATE_FIELDS | {"email", "password"})
        vr = self._validate_update_payload(clean)
        vr.merge(self._check_uniqueness(
            clean.get("email"), clean.get("phone"), exclude_user_id=user.id
        ))
        if not vr.ok:
            raise ValidationError("\n".join(e.message for e in vr.errors))

        vals = self._map_update_vals(clean)
        if vals:
            user.write(vals)
            _logger.audit(
                "User updated via service: id=%s fields=%s",
                user.id, list(vals.keys()),
                extra={"user_id": user.id, "action": "update_user"},
            )
        return user.to_public_dict()

    @api.model
    def archive_user(self, user_id: int) -> Dict[str, Any]:
        """Archive a user (Odoo ``active=False``; the record is kept)."""
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        user.write({"active": False, "x_status": "inactive"})
        _logger.audit(
            "User archived: id=%s", user.id,
            extra={"user_id": user.id, "action": "archive_user"},
        )
        return {"id": user.id, "active": False, "status": user.x_status}

    @api.model
    def restore_user(self, user_id: int) -> Dict[str, Any]:
        """Restore an archived user."""
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        user.write({"active": True, "x_status": "active"})
        _logger.audit(
            "User restored: id=%s", user.id,
            extra={"user_id": user.id, "action": "restore_user"},
        )
        return {"id": user.id, "active": True, "status": user.x_status}

    # ------------------------------------------------------------------ #
    # Status transitions
    # ------------------------------------------------------------------ #
    @api.model
    def set_status(self, user_id: int, status: str) -> Dict[str, Any]:
        """Change the account lifecycle status (active/suspended/pending/inactive)."""
        valid = {"active", "suspended", "pending", "inactive"}
        if status not in valid:
            raise ValidationError(
                f"status must be one of {sorted(valid)}."
            )
        user = self.env["res.users"].browse(user_id)
        if not user.exists():
            raise MissingError(f"User {user_id} not found.")
        user.write({"x_status": status})
        _logger.audit(
            "User status changed: id=%s status=%s", user.id, status,
            extra={"user_id": user.id, "action": "set_status", "new_status": status},
        )
        return {"id": user.id, "status": user.x_status}

    # ------------------------------------------------------------------ #
    # Mapping helpers (API field names -> ORM field names)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _whitelist(payload: Dict[str, Any], allowed: set) -> Dict[str, Any]:
        """Return a new dict containing only keys in ``allowed``."""
        return {k: v for k, v in payload.items() if k in allowed}

    @staticmethod
    def _map_create_vals(clean: Dict[str, Any]) -> Dict[str, Any]:
        """Map whitelisted API fields to the ``res.users`` ORM field names."""
        vals: Dict[str, Any] = {}
        if "name" in clean:
            vals["name"] = clean["name"]
        if "email" in clean:
            vals["login"] = EmailValidator.normalise(clean["email"])
            # Ensure the partner email is synced.
            vals["email"] = vals["login"]
        if "phone" in clean and not ValidationHelper.is_missing(clean["phone"]):
            vals["x_phone"] = PhoneValidator.normalise(clean["phone"])
        if "user_type" in clean and not ValidationHelper.is_missing(clean["user_type"]):
            vals["x_user_type"] = clean["user_type"]
        else:
            vals["x_user_type"] = UserType.CUSTOMER.value
        if "status" in clean and not ValidationHelper.is_missing(clean["status"]):
            vals["x_status"] = clean["status"]
        else:
            vals["x_status"] = "pending"
        if "password" in clean and not ValidationHelper.is_missing(clean["password"]):
            vals["password"] = clean["password"]
        if "avatar" in clean and not ValidationHelper.is_missing(clean["avatar"]):
            vals["x_avatar"] = clean["avatar"]
        return vals

    @staticmethod
    def _map_update_vals(clean: Dict[str, Any]) -> Dict[str, Any]:
        """Map whitelisted API fields for an update (no defaults)."""
        vals: Dict[str, Any] = {}
        if "name" in clean and not ValidationHelper.is_missing(clean["name"]):
            vals["name"] = clean["name"]
        if "email" in clean and not ValidationHelper.is_missing(clean["email"]):
            login = EmailValidator.normalise(clean["email"])
            vals["login"] = login
            vals["email"] = login
        if "phone" in clean:
            if ValidationHelper.is_missing(clean["phone"]):
                vals["x_phone"] = False
            else:
                vals["x_phone"] = PhoneValidator.normalise(clean["phone"])
        if "user_type" in clean and not ValidationHelper.is_missing(clean["user_type"]):
            vals["x_user_type"] = clean["user_type"]
        if "status" in clean and not ValidationHelper.is_missing(clean["status"]):
            vals["x_status"] = clean["status"]
        if "password" in clean and not ValidationHelper.is_missing(clean["password"]):
            vals["password"] = clean["password"]
        if "avatar" in clean:
            if ValidationHelper.is_missing(clean["avatar"]):
                vals["x_avatar"] = False
            else:
                vals["x_avatar"] = clean["avatar"]
        return vals
