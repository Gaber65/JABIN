from __future__ import annotations
from odoo import api, fields, models
from odoo.addons.jabin_core import JabinLogger
from odoo.addons.jabin_core.validators.phone_validator import PhoneValidator

_logger = JabinLogger.get('users.address')


class JabinUserAddress(models.Model):
    _name = 'res.users.address'
    _description = 'JABIN User Address'
    _order = 'is_default desc, id desc'

    user_id = fields.Many2one(
        comodel_name='res.users',  # Changed from res.users
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
        help='The JABIN user who owns this address.'
    )
    x_user_name = fields.Char(
        related='user_id.name',
        string='User Name',
        store=True,
        readonly=True
    )
    title = fields.Char(
        string='Title',
        required=True,
        help="Short label for the address (e.g. 'Home', 'Office', 'Warehouse')."
    )
    recipient_name = fields.Char(
        string='Recipient Name',
        required=True,
        help='Name of the person who will receive deliveries at this address.'
    )
    x_recipient_phone = fields.Char(
        string='Recipient Phone',
        help="Contact phone for the recipient (may differ from the user's phone)."
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
        required=True,
        help='Country of the delivery address.'
    )
    city = fields.Char(string='City', required=True, index=True)
    district = fields.Char(string='District / Area')
    street = fields.Char(string='Street Address', required=True)
    building = fields.Char(string='Building')
    floor = fields.Char(string='Floor')
    apartment = fields.Char(string='Apartment')
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    is_default = fields.Boolean(string='Default Address', default=False, index=True)
    create_date = fields.Datetime(string='Created On', readonly=True, index=True)
    write_date = fields.Datetime(string='Last Updated On', readonly=True)

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            self._normalize_vals(vals)
        records = super().create(vals_list)
        for rec in records:
            if rec.is_default:
                rec._ensure_single_default()
            _logger.audit(
                'Address created: id=%s user=%s title=%s',
                rec.id,
                rec.user_id.id,
                rec.title,
                extra={'address_id': rec.id, 'user_id': rec.user_id.id}
            )
        return records

    def write(self, vals):
        self._normalize_vals(vals)
        res = super().write(vals)
        if vals.get('is_default'):
            for rec in self:
                if rec.is_default:
                    rec._ensure_single_default()
        return res

    @staticmethod
    def _normalize_vals(vals: dict) -> None:
        if 'x_recipient_phone' in vals and vals['x_recipient_phone']:
            vals['x_recipient_phone'] = PhoneValidator.normalise(str(vals['x_recipient_phone'])) or False

    def _ensure_single_default(self) -> None:
        self.ensure_one()
        others = self.search([
            ('user_id', '=', self.user_id.id),
            ('is_default', '=', True),
            ('id', '!=', self.id)
        ])
        if others:
            others.write({'is_default': False})

    @api.model
    def find_by_user(self, user_id: int):
        return self.search(
            [('user_id', '=', user_id)],
            order='is_default desc, id desc'
        )

    @api.model
    def find_default(self, user_id: int):
        return self.search(
            [('user_id', '=', user_id), ('is_default', '=', True)],
            limit=1
        )

    @api.model
    def find_owned(self, address_id: int, user_id: int):
        if not address_id or not user_id:
            return self.env['res.users.address']
        return self.search([
            ('id', '=', address_id),
            ('user_id', '=', user_id)
        ], limit=1)

    def to_public_dict(self) -> dict:
        self.ensure_one()
        return {
            'id': self.id,
            'title': self.title,
            'recipient_name': self.recipient_name,
            'recipient_phone': self.x_recipient_phone or None,
            'country': {
                'id': self.country_id.id,
                'name': self.country_id.name,
                'code': self.country_id.code
            } if self.country_id else None,
            'city': self.city,
            'district': self.district or None,
            'street': self.street,
            'building': self.building or None,
            'floor': self.floor or None,
            'apartment': self.apartment or None,
            'latitude': self.latitude or None,
            'longitude': self.longitude or None,
            'is_default': self.is_default,
            'created_at': self.create_date.isoformat() if self.create_date else None,
            'updated_at': self.write_date.isoformat() if self.write_date else None,
        }