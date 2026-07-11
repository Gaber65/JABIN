# addons/jabin_user/models/jabin_user.py
from odoo import models, fields, api
from typing import Optional, Dict, Any


class JabinUser(models.Model):
    _name = 'jabin.user'
    _description = 'Jabin User'
    _rec_name = 'email'
    _order = 'id desc'

    # --- Fields ---
    name = fields.Char(string='Name', index=True)
    email = fields.Char(string='Email', required=True, index=True)
    phone = fields.Char(string='Phone', index=True)
    avatar = fields.Binary(string='Avatar', attachment=True)
    verified_at = fields.Datetime(string='Verified At', readonly=True)

    _sql_constraints = [
        (
            'jabin_user_email_unique',
            'unique(email)',
            'Email already exists.'
        )
    ]
    status = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive')
    ], string='Status', default='pending', required=True, index=True)

    profile_completed = fields.Boolean(string='Profile Completed', default=False)
    user_type = fields.Selection([
        ('individual', 'Individual'),
        ('business', 'Business')
    ], string='User Type', default='individual')

    balance = fields.Float(string='Balance', default=0.0)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self:
        self.env.company.currency_id.id
    )
    last_login = fields.Datetime(string='Last Login')

    # NOTE: password_hash is intentionally omitted. 
    # Authentication is strictly passwordless (Email + OTP).

    # --- Helper Methods ---
    @api.model
    def find_by_email(self, email: str) -> Optional['JabinUser']:
        """Find a user by email address."""
        return self.search([('email', '=', email)], limit=1)

    @api.model
    def find_by_phone(self, phone: str) -> Optional['JabinUser']:
        """Find a user by phone number."""
        return self.search([('phone', '=', phone)], limit=1)

    @api.model
    def find_by_login(self, email: str) -> Optional['JabinUser']:
        """Find a user by login (email)."""
        return self.search([('email', '=', email)], limit=1)

    def update_last_login(self) -> None:
        """Update the last login timestamp to now."""
        self.ensure_one()
        self.write({'last_login': fields.Datetime.now()})

    def to_public_dict(self) -> Dict[str, Any]:
        """Serialize user data for API responses."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'avatar': self.avatar,  # Note: Frontend should handle base64 if binary
            'status': self.status,
            'profile_completed': self.profile_completed,
            'user_type': self.user_type,
            'balance': self.balance,
            'currency_id': self.currency_id.id if self.currency_id else None,
            'last_login': self.last_login,
        }