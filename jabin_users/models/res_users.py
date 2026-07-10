from __future__ import annotations
from odoo import api, fields, models

from odoo.addons.jabin_core import JabinLogger
from odoo.addons.jabin_core.constants.user_types import UserType

_logger = JabinLogger.get('jabin.user')


class JabinUser(models.Model):
    _name = 'jabin.user'
    _description = 'JABIN User'
    _order = 'id desc'

    # -------------------------
    # Basic Information
    # -------------------------

    name = fields.Char(
        string='Name',
        required=True,
        index=True
    )

    login = fields.Char(
        string='Email',
        required=True,
        index=True
    )

    password_hash = fields.Char(
        string='Password Hash',
        required=True
    )

    # -------------------------
    # Account Classification
    # -------------------------

    user_type = fields.Selection(
        selection=lambda self: [
            (item.value, item.label)
            for item in UserType
        ],
        string='User Type',
        default=UserType.CUSTOMER.value,
        required=True,
        index=True
    )

    # -------------------------
    # Contact
    # -------------------------

    phone = fields.Char(
        string='Phone',
        index=True
    )

    avatar = fields.Image(
        string='Avatar',
        max_width=512,
        max_height=512
    )

    # -------------------------
    # Wallet
    # -------------------------

    balance = fields.Monetary(
        string='Balance',
        currency_field='currency_id',
        default=0
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self:
        self.env.company.currency_id.id
    )

    # -------------------------
    # Status
    # -------------------------

    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('inactive', 'Inactive'),
        ],
        string='Status',
        default='pending',
        required=True,
        index=True
    )

    is_active = fields.Boolean(
        compute='_compute_is_active',
        store=True
    )

    profile_completed = fields.Boolean(
        string='Profile Completed',
        default=False
    )

    # -------------------------
    # Authentication Tracking
    # -------------------------

    last_login = fields.Datetime(
        readonly=True
    )

    created_at = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True
    )

    # -------------------------
    # Constraints
    # -------------------------

    _sql_constraints = [

        (
            'email_unique',
            'unique(email)',
            'Email already exists.'
        ),

        (
            'phone_unique',
            'unique(phone)',
            'Phone already exists.'
        ),

    ]

    # -------------------------
    # Compute
    # -------------------------

    @api.depends('status')
    def _compute_is_active(self):

        for user in self:
            user.is_active = (
                    user.status == 'active'
            )

    # -------------------------
    # CRUD
    # -------------------------

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            self._normalize(vals)

        users = super().create(vals_list)

        for user in users:
            _logger.audit(
                'JABIN user created id=%s',
                user.id,
                extra={
                    'user_id': user.id
                }
            )

        return users

    def write(self, vals):

        self._normalize(vals)

        return super().write(vals)

    # -------------------------
    # Helpers
    # -------------------------

    @staticmethod
    def _normalize(vals):

        if vals.get('email'):
            vals['email'] = (
                vals['email']
                .strip()
                .lower()
            )

        if vals.get('phone'):
            raw = str(vals['phone']).strip()

            prefix = (
                '+'
                if raw.startswith('+')
                else ''
            )

            digits = ''.join(
                c for c in raw
                if c.isdigit()
            )

            vals['phone'] = (
                f'{prefix}{digits}'
                if digits
                else False
            )

    # -------------------------
    # Search
    # -------------------------

    @api.model
    def find_by_login(self, login):

        if not login:
            return self.browse()

        return self.search(
            [
                (
                    'login',
                    '=',
                    login.strip().lower()
                )
            ],
            limit=1
        )

    @api.model
    def find_by_phone(self, phone):

        if not phone:
            return self.browse()

        self._normalize(
            {
                'phone': phone
            }
        )

        return self.search(
            [
                (
                    'phone',
                    '=',
                    phone
                )
            ],
            limit=1
        )

    # -------------------------
    # Authentication
    # -------------------------

    def update_last_login(self):

        self.write(
            {
                'last_login':
                    fields.Datetime.now()
            }
        )

    # -------------------------
    # API Response
    # -------------------------

    def to_public_dict(self):

        self.ensure_one()

        return {

            'id':
                self.id,

            'name':
                self.name,

            'email':
                self.login,

            'phone':
                self.phone,

            'user_type':
                self.user_type,

            'status':
                self.status,

            'avatar':
                bool(self.avatar),

            'balance':
                self.balance,

            'currency':
                self.currency_id.name
                if self.currency_id
                else None,

            'profile_completed':
                self.profile_completed,

            'last_login':
                self.last_login.isoformat()
                if self.last_login
                else None,

        }
