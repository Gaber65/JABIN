from __future__ import annotations
from odoo import api, fields, models
from odoo.addons.jabin_core import JabinLogger
from odoo.addons.jabin_core.constants.user_types import UserType

_logger = JabinLogger.get('users.model')


class JabinUser(models.Model):
    _inherit = 'res.users'
    _description = 'JABIN User'
    x_user_type = fields.Selection(
        selection=lambda self: [(t.value, t.label) for t in UserType],
        string='User Type',
        default=UserType.CUSTOMER.value,
        required=True,
        index=True,
        help='Classifies the account (admin, customer, manager, employee, driver).'
    )
    x_phone = fields.Char(string='Phone', index=True,
                          help='Phone number in E.164-ish form; used for phone-based login.')
    x_avatar = fields.Image(string='Avatar', max_width=512, max_height=512,
                            help='Profile picture (stored as binary, may be served as a URL).')
    x_balance = fields.Monetary(string='Balance', currency_field='x_currency_id', default=0.0,
                                help="Wallet / credit balance in the user's currency.")
    x_currency_id = fields.Many2one(comodel_name='res.currency', string='Currency',
                                    default=lambda self: self.env.ref('base.main_company').currency_id,
                                    help='Currency used for the balance field.')
    x_status = fields.Selection(
        selection=[('active', 'Active'), ('suspended', 'Suspended'), ('pending', 'Pending'), ('inactive', 'Inactive')],
        string='Account Status', default='pending', required=True, index=True, help='Lifecycle status of the account.')
    x_last_login = fields.Datetime(string='Last Login', readonly=True,
                                   help='Timestamp of the last successful authentication.')
    x_is_active_account = fields.Boolean(string='Account Active', compute='_compute_x_is_active_account', store=True,
                                         help="Technical flag: True when status == 'active'.")

    @api.depends('x_status')
    def _compute_x_is_active_account(self):
        for rec in self:
            rec.x_is_active_account = rec.x_status == 'active'

    _sql_constraints = [('x_phone_unique', 'unique(x_phone)', 'A user with this phone number already exists.')]

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            self._normalize_vals(vals)
        users = super().create(vals_list)
        for user in users:
            _logger.audit('User created: id=%s type=%s', user.id, user.x_user_type, extra={'user_id': user.id})
        return users

    def write(self, vals):
        self._normalize_vals(vals)
        return super().write(vals)

    @staticmethod
    def _normalize_vals(vals: dict) -> None:
        if 'x_phone' in vals and vals['x_phone']:
            raw = str(vals['x_phone']).strip()
            leading_plus = '+' if raw.startswith('+') else ''
            digits = ''.join((ch for ch in raw if ch.isdigit()))
            vals['x_phone'] = f'{leading_plus}{digits}' or False
        if 'login' in vals and vals['login']:
            vals['login'] = str(vals['login']).strip().lower()

    @api.model
    def find_by_login(self, login: str):
        if not login:
            return self.env['res.users']
        return self.search([('login', '=', str(login).strip().lower())], limit=1)

    @api.model
    def find_by_phone(self, phone: str):
        if not phone:
            return self.env['res.users']
        raw = str(phone).strip()
        leading_plus = '+' if raw.startswith('+') else ''
        digits = ''.join((ch for ch in raw if ch.isdigit()))
        normalized = f'{leading_plus}{digits}'
        if not normalized:
            return self.env['res.users']
        return self.search([('x_phone', '=', normalized)], limit=1)

    def to_public_dict(self) -> dict:
        self.ensure_one()
        return {'id': self.id, 'name': self.name, 'email': self.login, 'phone': self.x_phone or None,
                'user_type': self.x_user_type, 'status': self.x_status, 'balance': self.x_balance,
                'currency': self.x_currency_id.name if self.x_currency_id else None, 'avatar': bool(self.x_avatar),
                'last_login': self.x_last_login.isoformat() if self.x_last_login else None,
                'is_active_account': self.x_is_active_account}
