# -*- coding: utf-8 -*-
"""JABIN user profile -- extension of Odoo's ``res.users``.

This is the central identity model of the platform. Rather than creating a
parallel ``jabin.user`` table (which would duplicate authentication, sessions,
access rights and partner linkage), we **extend** ``res.users`` with the
JABIN-specific business fields. This is the Odoo 17 best practice: it reuses
the framework's password hashing, session management, multi-company rules,
and access-rights engine for free.

JABIN-specific fields
---------------------
* ``x_user_type``   -- one of :class:`~jabin_core.constants.user_types.UserType`
  (admin / customer / manager / employee / driver). Prefixed with ``x_`` to
  make it visually distinct from native Odoo fields and avoid name clashes with
  future Odoo versions.
* ``x_phone``       -- E.164-ish phone, used for phone-based login.
* ``x_avatar``      -- profile picture (binary or URL).
* ``x_balance``     -- wallet/credit balance (monetary, Decimal-safe).
* ``x_status``      -- account lifecycle status (active / suspended / pending /
  inactive).
* ``x_last_login``  -- last successful login timestamp.

Constraints
-----------
* ``login`` (Odoo native, = email) must be unique and valid.
* ``x_phone``, when set, must be unique.
* ``x_user_type`` must be a known ``UserType`` value.

Why store fields as ``x_`` prefixed?
------------------------------------
Keeping the JABIN namespace explicit prevents collisions with Odoo's own
fields and signals to developers that these are custom business attributes.
The services layer hides this detail behind clean accessor names.

Extensibility
-------------
* Wallet/transactions will extend ``x_balance`` in a later sprint.
* Per-tenant user-type policies can be layered on by overriding ``create`` /
  ``write`` here or in a dedicated service.
"""

from __future__ import annotations

from odoo import api, fields, models

from jabin_core import JabinLogger
from jabin_core.constants.user_types import UserType


# Module-level logger for this model's internal events (constraint failures,
# lifecycle changes). Created once; reused across method calls.
_logger = JabinLogger.get("users.model")


class JabinUser(models.Model):
    """Extended ``res.users`` carrying JABIN business fields."""

    _inherit = "res.users"
    _description = "JABIN User"

    # ------------------------------------------------------------------ #
    # JABIN business fields
    # ------------------------------------------------------------------ #
    x_user_type = fields.Selection(
        selection=lambda: [(t.value, t.label) for t in UserType],
        string="User Type",
        default=UserType.CUSTOMER.value,
        required=True,
        index=True,
        help="Classifies the account (admin, customer, manager, employee, driver).",
    )
    x_phone = fields.Char(
        string="Phone",
        index=True,
        help="Phone number in E.164-ish form; used for phone-based login.",
    )
    x_avatar = fields.Image(
        string="Avatar",
        max_width=512,
        max_height=512,
        help="Profile picture (stored as binary, may be served as a URL).",
    )
    x_balance = fields.Monetary(
        string="Balance",
        currency_field="x_currency_id",
        default=0.0,
        help="Wallet / credit balance in the user's currency.",
    )
    x_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.ref("base.main_company").currency_id,
        help="Currency used for the balance field.",
    )
    x_status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("pending", "Pending"),
            ("inactive", "Inactive"),
        ],
        string="Account Status",
        default="pending",
        required=True,
        index=True,
        help="Lifecycle status of the account.",
    )
    x_last_login = fields.Datetime(
        string="Last Login",
        readonly=True,
        help="Timestamp of the last successful authentication.",
    )
    # Convenience flag: a user is "usable" only when active and not a portal
    # technical user. Computed for fast filtering in services.
    x_is_active_account = fields.Boolean(
        string="Account Active",
        compute="_compute_x_is_active_account",
        store=True,
        help="Technical flag: True when status == 'active'.",
    )

    # ------------------------------------------------------------------ #
    # Computes
    # ------------------------------------------------------------------ #
    @api.depends("x_status")
    def _compute_x_is_active_account(self):
        for rec in self:
            rec.x_is_active_account = rec.x_status == "active"

    # ------------------------------------------------------------------ #
    # SQL constraints (uniqueness at the DB level)
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        (
            "x_phone_unique",
            "unique(x_phone)",
            "A user with this phone number already exists.",
        ),
    ]

    # ------------------------------------------------------------------ #
    # ORM overrides
    # ------------------------------------------------------------------ #
    @api.model
    def create(self, vals_list):
        """Normalize phone + lower-case email on creation and log the event."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            self._normalize_vals(vals)
        users = super().create(vals_list)
        for user in users:
            _logger.audit(
                "User created: id=%s type=%s", user.id, user.x_user_type,
                extra={"user_id": user.id},
            )
        return users

    def write(self, vals):
        """Normalize phone on write and guard sensitive fields."""
        self._normalize_vals(vals)
        return super().write(vals)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_vals(vals: dict) -> None:
        """In-place normalization of phone / email before persistence.

        Mutates ``vals`` directly to avoid creating throwaway dicts.
        """
        if "x_phone" in vals and vals["x_phone"]:
            # Strip everything but digits and a leading '+'. This matches the
            # normalization rule in PhoneValidator (Sprint 1).
            raw = str(vals["x_phone"]).strip()
            leading_plus = "+" if raw.startswith("+") else ""
            digits = "".join(ch for ch in raw if ch.isdigit())
            vals["x_phone"] = f"{leading_plus}{digits}" or False
        if "login" in vals and vals["login"]:
            vals["login"] = str(vals["login"]).strip().lower()

    # ------------------------------------------------------------------ #
    # Domain query helpers (used by the service layer)
    # ------------------------------------------------------------------ #
    @api.model
    def find_by_login(self, login: str):
        """Return the first user matching ``login`` (email, case-insensitive).

        Returns an empty recordset when not found. This is the single source
        of truth for "resolve a user by email" so auth logic never duplicates
        the lookup.
        """
        if not login:
            return self.env["res.users"]
        return self.search(
            [("login", "=", str(login).strip().lower())], limit=1
        )

    @api.model
    def find_by_phone(self, phone: str):
        """Return the first user matching the normalized ``phone``.

        Returns an empty recordset when not found or when ``phone`` is blank.
        """
        if not phone:
            return self.env["res.users"]
        raw = str(phone).strip()
        leading_plus = "+" if raw.startswith("+") else ""
        digits = "".join(ch for ch in raw if ch.isdigit())
        normalized = f"{leading_plus}{digits}"
        if not normalized:
            return self.env["res.users"]
        return self.search([("x_phone", "=", normalized)], limit=1)

    # ------------------------------------------------------------------ #
    # Serialization (used by the service / controllers)
    # ------------------------------------------------------------------ #
    def to_public_dict(self) -> dict:
        """Return a JSON-safe dict of non-sensitive user fields.

        **Never** includes ``password`` or password hashes. This is the only
        sanctioned serialization for API responses; controllers must use it.
        """
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "email": self.login,
            "phone": self.x_phone or None,
            "user_type": self.x_user_type,
            "status": self.x_status,
            "balance": self.x_balance,
            "currency": self.x_currency_id.name if self.x_currency_id else None,
            "avatar": bool(self.x_avatar),
            "last_login": self.x_last_login.isoformat() if self.x_last_login else None,
            "is_active_account": self.x_is_active_account,
        }
