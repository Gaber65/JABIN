# -*- coding: utf-8 -*-
"""Multi-address model for JABIN users.

A user may own several delivery addresses (home, work, warehouse drop-off, …).
Each address carries enough structured fields for last-mile delivery in the
markets JABIN operates in, plus optional GPS coordinates for mapping and
route-optimisation integrations that will arrive in later sprints.

Design decisions
----------------
* **Separate model, not ``res.partner``** – Odoo's ``res.partner`` is a
  heavyweight address book with its own access rules, companies, and
  accounting linkage. For lightweight delivery addresses that belong to a
  single user we keep a dedicated ``jabin.user.address`` table. This keeps the
  domain model clean and avoids side-effects on the partner registry.
* **``x_`` field prefix** – consistent with ``JabinUser`` so JABIN fields are
  visually distinct from any native Odoo fields that might appear on the same
  table.
* **Single default per user** – enforced at the model level: when a record is
  marked default, any other default belonging to the same user is cleared
  automatically (see :meth:`_ensure_single_default`).
* **Reuses Sprint 1 validators** – phone normalisation is delegated to
  :class:`~jabin_core.PhoneValidator` so the same rule applies everywhere.

Extensibility
-------------
* Geocoding hooks can be added as a computed field that calls an external
  service, gated behind a config flag.
* A ``verified`` boolean can be added when address verification (SMS OTP to
  the address phone) is introduced.
"""

from __future__ import annotations

from odoo import api, fields, models

from jabin_core import JabinLogger
from jabin_core.validators.phone_validator import PhoneValidator

_logger = JabinLogger.get("users.address")


class JabinUserAddress(models.Model):
    """Delivery / billing address owned by a single JABIN user."""

    _name = "jabin.user.address"
    _description = "JABIN User Address"
    _order = "is_default desc, id desc"

    # ------------------------------------------------------------------ #
    # Relations
    # ------------------------------------------------------------------ #
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
        help="The JABIN user who owns this address.",
    )
    # Convenience: mirror the user's display name for quick filtering.
    x_user_name = fields.Char(
        related="user_id.name",
        string="User Name",
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------------ #
    # Address label / recipient
    # ------------------------------------------------------------------ #
    title = fields.Char(
        string="Title",
        required=True,
        help="Short label for the address (e.g. 'Home', 'Office', 'Warehouse').",
    )
    recipient_name = fields.Char(
        string="Recipient Name",
        required=True,
        help="Name of the person who will receive deliveries at this address.",
    )
    x_recipient_phone = fields.Char(
        string="Recipient Phone",
        help="Contact phone for the recipient (may differ from the user's phone).",
    )

    # ------------------------------------------------------------------ #
    # Geographic / structured address
    # ------------------------------------------------------------------ #
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Country",
        required=True,
        help="Country of the delivery address.",
    )
    city = fields.Char(
        string="City",
        required=True,
        index=True,
        help="City / town.",
    )
    district = fields.Char(
        string="District / Area",
        help="Sub-city district or neighbourhood.",
    )
    street = fields.Char(
        string="Street Address",
        required=True,
        help="Street name and building number.",
    )
    building = fields.Char(
        string="Building",
        help="Building name or number.",
    )
    floor = fields.Char(
        string="Floor",
        help="Floor number (for apartment buildings).",
    )
    apartment = fields.Char(
        string="Apartment",
        help="Apartment / unit number.",
    )

    # Optional GPS coordinates for mapping / route optimisation.
    latitude = fields.Float(
        string="Latitude",
        digits=(10, 7),
        help="GPS latitude (WGS84). Optional; used for mapping.",
    )
    longitude = fields.Float(
        string="Longitude",
        digits=(10, 7),
        help="GPS longitude (WGS84). Optional; used for mapping.",
    )

    # ------------------------------------------------------------------ #
    # Default flag
    # ------------------------------------------------------------------ #
    is_default = fields.Boolean(
        string="Default Address",
        default=False,
        index=True,
        help="If checked, this is the user's default delivery address. "
             "Only one address per user may be default.",
    )

    # ------------------------------------------------------------------ #
    # Audit (lightweight; full audit mixin can be inherited later if needed)
    # ------------------------------------------------------------------ #
    create_date = fields.Datetime(
        string="Created On",
        readonly=True,
        index=True,
    )
    write_date = fields.Datetime(
        string="Last Updated On",
        readonly=True,
    )

    # ------------------------------------------------------------------ #
    # SQL constraints
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        # A recipient phone, when provided, is normalised before persistence
        # so a plain uniqueness check is not meaningful at this layer.
        # Uniqueness of "default per user" is enforced in code via
        # _ensure_single_default to allow toggling in a single transaction.
    ]

    # ------------------------------------------------------------------ #
    # ORM overrides
    # ------------------------------------------------------------------ #
    @api.model
    def create(self, vals_list):
        """Normalise phone and enforce single-default on creation."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            self._normalize_vals(vals)
        records = super().create(vals_list)
        for rec in records:
            if rec.is_default:
                rec._ensure_single_default()
            _logger.audit(
                "Address created: id=%s user=%s title=%s",
                rec.id, rec.user_id.id, rec.title,
                extra={"address_id": rec.id, "user_id": rec.user_id.id},
            )
        return records

    def write(self, vals):
        """Normalise phone and enforce single-default on write."""
        self._normalize_vals(vals)
        res = super().write(vals)
        if vals.get("is_default"):
            for rec in self:
                if rec.is_default:
                    rec._ensure_single_default()
        return res

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_vals(vals: dict) -> None:
        """In-place normalisation of the recipient phone field."""
        if "x_recipient_phone" in vals and vals["x_recipient_phone"]:
            vals["x_recipient_phone"] = PhoneValidator.normalise(
                str(vals["x_recipient_phone"])
            ) or False

    def _ensure_single_default(self) -> None:
        """Clear ``is_default`` on all other addresses of the same user.

        Called after a record becomes the default so that exactly one address
        is default per user at all times. The current recordset is excluded
        from the reset.
        """
        self.ensure_one()
        others = self.search([
            ("user_id", "=", self.user_id.id),
            ("is_default", "=", True),
            ("id", "!=", self.id),
        ])
        if others:
            others.write({"is_default": False})

    # ------------------------------------------------------------------ #
    # Domain query helpers (used by the service layer)
    # ------------------------------------------------------------------ #
    @api.model
    def find_by_user(self, user_id: int):
        """Return all addresses belonging to ``user_id``, default first."""
        return self.search(
            [("user_id", "=", user_id)],
            order="is_default desc, id desc",
        )

    @api.model
    def find_default(self, user_id: int):
        """Return the default address for ``user_id`` (or empty recordset)."""
        return self.search(
            [("user_id", "=", user_id), ("is_default", "=", True)],
            limit=1,
        )

    @api.model
    def find_owned(self, address_id: int, user_id: int):
        """Return the address if it belongs to ``user_id`` (or empty recordset).

        This is the single source of truth for ownership checks so controllers
        can avoid ad-hoc domains.
        """
        if not address_id or not user_id:
            return self.env["jabin.user.address"]
        return self.search(
            [("id", "=", address_id), ("user_id", "=", user_id)],
            limit=1,
        )

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #
    def to_public_dict(self) -> dict:
        """Return a JSON-safe dict of the address fields."""
        self.ensure_one()
        return {
            "id": self.id,
            "title": self.title,
            "recipient_name": self.recipient_name,
            "recipient_phone": self.x_recipient_phone or None,
            "country": {
                "id": self.country_id.id,
                "name": self.country_id.name,
                "code": self.country_id.code,
            } if self.country_id else None,
            "city": self.city,
            "district": self.district or None,
            "street": self.street,
            "building": self.building or None,
            "floor": self.floor or None,
            "apartment": self.apartment or None,
            "latitude": self.latitude or None,
            "longitude": self.longitude or None,
            "is_default": self.is_default,
            "created_at": self.create_date.isoformat() if self.create_date else None,
            "updated_at": self.write_date.isoformat() if self.write_date else None,
        }
