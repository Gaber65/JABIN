from odoo import models, fields, api, _
from typing import Optional, Dict, Any


class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = 'Jabin User (Extended)'

    # --- Custom Fields (preserved from res.users) ---
    verified_at = fields.Datetime(string='Verified At', readonly=True)

    status = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive')
    ], string='Status', default='pending', required=True, index=True)

    profile_completed = fields.Boolean(string='Profile Completed', default=False)


    addresses = fields.One2many(
        'res.users.address',
        'user_id',
        string='Addresses'
    )

    user_type = fields.Selection([
        ('individual', 'Individual'),
        ('business', 'Business')
    ], string='User Type', default='individual')

    balance = fields.Float(string='Balance', default=0.0)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    last_login = fields.Datetime(string='Last Login')

    # avatar is replaced by image_1920 from res.users

    # --- Override create to set default values ---
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Ensure login is set from email if not provided
            if 'email' in vals and 'login' not in vals:
                vals['login'] = vals['email']
            # Ensure partner email is set
            if 'email' in vals and 'partner_id' not in vals:
                # Partner will be created automatically with email
                pass
        return super().create(vals_list)

    # --- Helper Methods (adapted from res.users) ---
    @api.model
    def find_by_email(self, email: str) -> Optional['ResUsers']:
        """Find a user by email address."""
        return self.search([('login', '=', email)], limit=1)

    @api.model
    def find_by_phone(self, phone: str) -> Optional['ResUsers']:
        """Find a user by phone number."""
        return self.search([('partner_id.phone', '=', phone)], limit=1)

    @api.model
    def find_by_login(self, email: str) -> Optional['ResUsers']:
        """Find a user by login (email)."""
        return self.search([('login', '=', email)], limit=1)

    def update_last_login(self) -> None:
        """Update the last login timestamp to now."""
        self.ensure_one()
        self.write({'last_login': fields.Datetime.now()})

    def get_role_codes(self) -> list:
        """Get the role codes assigned to this user."""
        roles = self.env['jabin.role'].search([
            ('user_ids', 'in', self.id)
        ])
        return roles.mapped('code')

    def get_permission_codes(self) -> set:
        """Get the permission codes for this user."""
        roles = self.env['jabin.role'].search([
            ('user_ids', 'in', self.id)
        ])
        permissions = roles.mapped('permission_ids')
        return set(permissions.mapped('code'))

    def to_public_dict(self) -> Dict[str, Any]:
        """Serialize user data for API responses."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'email': self.login,  # Use login as email
            'phone': self.partner_id.phone if self.partner_id else None,
            'avatar': self.image_1920,  # Use built-in avatar field
            'status': self.status,
            'profile_completed': self.profile_completed,
            'user_type': self.user_type,
            'balance': self.balance,
            'currency_id': self.currency_id.id if self.currency_id else None,
            'last_login': self.last_login,
            'verified_at': self.verified_at,
        }
