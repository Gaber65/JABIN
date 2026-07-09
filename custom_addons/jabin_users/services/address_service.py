# -*- coding: utf-8 -*-
"""Address service for the JABIN platform.

Business logic for the multi-address model. Controllers call this service for
all address CRUD; no ORM calls should appear in controllers.

Responsibilities
----------------
* CRUD for ``jabin.user.address`` records, scoped to the owning user.
* **Ownership enforcement** – every read / update / delete verifies the
  address belongs to the requesting user (prevents IDOR).
* Validation of incoming payloads (title, recipient, country, city, street,
  phone, coordinates).
* Single-default enforcement is handled by the model, but the service
  coordinates setting the default when none exists yet.
* Audit logging of every mutation.

Design rules
------------
* Same patterns as ``UserService``: AbstractModel service, raises Odoo
  exceptions, whitelists input.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from odoo import api, models
from odoo.exceptions import MissingError, ValidationError

from jabin_core import (
    JabinLogger,
    PaginationHelper,
    PhoneValidator,
    ValidationResult,
    ValidationHelper,
)

_logger = JabinLogger.get("users.address_service")

# Whitelisted fields for create / update (prevents mass-assignment).
_ADDRESS_FIELDS = {
    "title", "recipient_name", "recipient_phone",
    "country_id", "country_code",
    "city", "district", "street", "building", "floor", "apartment",
    "latitude", "longitude", "is_default",
}


class AddressService(models.AbstractModel):
    """Business-logic service for JABIN user addresses."""

    _name = "jabin.address.service"
    _description = "JABIN Address Service"

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @api.model
    def _validate_payload(self, payload: Dict[str, Any], *, is_update: bool = False) -> ValidationResult:
        """Validate an address create or update payload."""
        result = ValidationResult()

        if not is_update:
            result.require("title", payload.get("title"))
            result.require("recipient_name", payload.get("recipient_name"))
            result.require("country_code", payload.get("country_code"))
            result.require("city", payload.get("city"))
            result.require("street", payload.get("street"))

        # Phone (optional)
        phone = payload.get("recipient_phone")
        if phone and not ValidationHelper.is_missing(phone):
            result.merge(PhoneValidator.validate(phone, field="recipient_phone"))

        # Coordinates (optional, but if present must be numeric)
        for coord_field in ("latitude", "longitude"):
            val = payload.get(coord_field)
            if val is not None and not ValidationHelper.is_missing(val):
                if not ValidationHelper.is_float(val):
                    result.add(
                        f"{coord_field} must be a number.",
                        field=coord_field,
                    )
                else:
                    v = float(val)
                    if coord_field == "latitude" and not (-90.0 <= v <= 90.0):
                        result.add(
                            "latitude must be between -90 and 90.",
                            field="latitude",
                        )
                    if coord_field == "longitude" and not (-180.0 <= v <= 180.0):
                        result.add(
                            "longitude must be between -180 and 180.",
                            field="longitude",
                        )

        # Country code -> resolve to country_id
        code = payload.get("country_code")
        if code and not ValidationHelper.is_missing(code):
            country = self.env["res.country"].search(
                [("code", "=", str(code).upper().strip())], limit=1
            )
            if not country:
                result.add(
                    f"country_code '{code}' is not a recognised ISO country code.",
                    field="country_code",
                )

        return result

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    @api.model
    def create_address(self, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new address for ``user_id``.

        If this is the user's first address, it is automatically marked as
        default regardless of the ``is_default`` flag in the payload.
        """
        clean = self._whitelist(payload, _ADDRESS_FIELDS)
        vr = self._validate_payload(clean)
        if not vr.ok:
            raise ValidationError("\n".join(e.message for e in vr.errors))

        # Resolve country
        country = self._resolve_country(clean.get("country_code"))
        if not country:
            raise ValidationError("country_code is required.")

        # First address for the user -> auto-default.
        existing = self.env["jabin.user.address"].search_count(
            [("user_id", "=", user_id)]
        )
        is_default = clean.get("is_default", False) if existing else True

        vals = self._map_vals(clean, country_id=country.id)
        vals["user_id"] = user_id
        vals["is_default"] = bool(is_default)

        addr = self.env["jabin.user.address"].create(vals)
        _logger.audit(
            "Address created: id=%s user=%s",
            addr.id, user_id,
            extra={"address_id": addr.id, "user_id": user_id, "action": "create_address"},
        )
        return addr.to_public_dict()

    @api.model
    def get_address(self, address_id: int, user_id: int) -> Dict[str, Any]:
        """Return a single address, verifying ownership.

        Raises ``MissingError`` if the address does not exist or does not
        belong to ``user_id``.
        """
        addr = self.env["jabin.user.address"].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f"Address {address_id} not found for user {user_id}.")
        return addr.to_public_dict()

    @api.model
    def list_addresses(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return a paginated list of addresses for ``user_id``."""
        domain = [("user_id", "=", user_id)]
        Addr = self.env["jabin.user.address"]
        total = Addr.search_count(domain)
        meta = PaginationHelper.meta_dict(total, page, per_page)
        offset, limit = PaginationHelper.offset_limit(page, per_page)
        addresses = Addr.search(domain, offset=offset, limit=limit)
        return [a.to_public_dict() for a in addresses], meta

    @api.model
    def update_address(
        self, address_id: int, user_id: int, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an address, verifying ownership."""
        addr = self.env["jabin.user.address"].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f"Address {address_id} not found for user {user_id}.")

        clean = self._whitelist(payload, _ADDRESS_FIELDS)
        vr = self._validate_payload(clean, is_update=True)
        if not vr.ok:
            raise ValidationError("\n".join(e.message for e in vr.errors))

        vals = self._map_vals(clean, country_id=self._resolve_country(clean.get("country_code")))
        if vals:
            addr.write(vals)
            _logger.audit(
                "Address updated: id=%s user=%s fields=%s",
                addr.id, user_id, list(vals.keys()),
                extra={"address_id": addr.id, "user_id": user_id, "action": "update_address"},
            )
        return addr.to_public_dict()

    @api.model
    def delete_address(self, address_id: int, user_id: int) -> Dict[str, Any]:
        """Permanently delete an address, verifying ownership.

        If the deleted address was the default, the most recent remaining
        address is promoted to default automatically.
        """
        addr = self.env["jabin.user.address"].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f"Address {address_id} not found for user {user_id}.")

        was_default = addr.is_default
        addr.unlink()
        _logger.audit(
            "Address deleted: id=%s user=%s",
            address_id, user_id,
            extra={"address_id": address_id, "user_id": user_id, "action": "delete_address"},
        )

        if was_default:
            # Promote the latest remaining address to default.
            next_addr = self.env["jabin.user.address"].search(
                [("user_id", "=", user_id)], order="id desc", limit=1
            )
            if next_addr:
                next_addr.write({"is_default": True})

        return {"id": address_id, "deleted": True}

    @api.model
    def set_default(self, address_id: int, user_id: int) -> Dict[str, Any]:
        """Mark an address as the user's default."""
        addr = self.env["jabin.user.address"].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f"Address {address_id} not found for user {user_id}.")
        addr.write({"is_default": True})
        _logger.audit(
            "Address set default: id=%s user=%s", addr.id, user_id,
            extra={"address_id": addr.id, "user_id": user_id, "action": "set_default"},
        )
        return {"id": addr.id, "is_default": True}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _whitelist(payload: Dict[str, Any], allowed: set) -> Dict[str, Any]:
        return {k: v for k, v in payload.items() if k in allowed}

    @api.model
    def _resolve_country(self, code: Optional[str]):
        """Return the ``res.country`` record matching ``code`` or empty recordset."""
        if not code or ValidationHelper.is_missing(code):
            return self.env["res.country"]
        return self.env["res.country"].search(
            [("code", "=", str(code).upper().strip())], limit=1
        )

    @staticmethod
    def _map_vals(clean: Dict[str, Any], country_id: Optional[int] = None) -> Dict[str, Any]:
        """Map whitelisted payload fields to ORM field names."""
        vals: Dict[str, Any] = {}
        if "title" in clean and not ValidationHelper.is_missing(clean["title"]):
            vals["title"] = clean["title"]
        if "recipient_name" in clean and not ValidationHelper.is_missing(clean["recipient_name"]):
            vals["recipient_name"] = clean["recipient_name"]
        if "recipient_phone" in clean:
            if ValidationHelper.is_missing(clean["recipient_phone"]):
                vals["x_recipient_phone"] = False
            else:
                vals["x_recipient_phone"] = PhoneValidator.normalise(clean["recipient_phone"])
        if country_id:
            vals["country_id"] = country_id
        if "city" in clean and not ValidationHelper.is_missing(clean["city"]):
            vals["city"] = clean["city"]
        if "district" in clean:
            vals["district"] = clean["district"] or False
        if "street" in clean and not ValidationHelper.is_missing(clean["street"]):
            vals["street"] = clean["street"]
        if "building" in clean:
            vals["building"] = clean["building"] or False
        if "floor" in clean:
            vals["floor"] = clean["floor"] or False
        if "apartment" in clean:
            vals["apartment"] = clean["apartment"] or False
        if "latitude" in clean and not ValidationHelper.is_missing(clean.get("latitude")):
            vals["latitude"] = float(clean["latitude"])
        if "longitude" in clean and not ValidationHelper.is_missing(clean.get("longitude")):
            vals["longitude"] = float(clean["longitude"])
        if "is_default" in clean:
            vals["is_default"] = bool(clean["is_default"])
        return vals
