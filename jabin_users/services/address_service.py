from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from odoo import api, models
from odoo.exceptions import MissingError, ValidationError
from odoo.addons.jabin_core import JabinLogger, PaginationHelper, PhoneValidator, ValidationResult, ValidationHelper
_logger = JabinLogger.get('users.address_service')
_ADDRESS_FIELDS = {'title', 'recipient_name', 'recipient_phone', 'country_id', 'country_code', 'city', 'district', 'street', 'building', 'floor', 'apartment', 'latitude', 'longitude', 'is_default'}

class AddressService(models.AbstractModel):
    _name = 'jabin.address.service'
    _description = 'JABIN Address Service'

    @api.model
    def _validate_payload(self, payload: Dict[str, Any], *, is_update: bool=False) -> ValidationResult:
        result = ValidationResult()
        if not is_update:
            result.require('title', payload.get('title'))
            result.require('recipient_name', payload.get('recipient_name'))
            result.require('country_code', payload.get('country_code'))
            result.require('city', payload.get('city'))
            result.require('street', payload.get('street'))
        phone = payload.get('recipient_phone')
        if phone and (not ValidationHelper.is_missing(phone)):
            result.merge(PhoneValidator.validate(phone, field='recipient_phone'))
        for coord_field in ('latitude', 'longitude'):
            val = payload.get(coord_field)
            if val is not None and (not ValidationHelper.is_missing(val)):
                if not ValidationHelper.is_float(val):
                    result.add(f'{coord_field} must be a number.', field=coord_field)
                else:
                    v = float(val)
                    if coord_field == 'latitude' and (not -90.0 <= v <= 90.0):
                        result.add('latitude must be between -90 and 90.', field='latitude')
                    if coord_field == 'longitude' and (not -180.0 <= v <= 180.0):
                        result.add('longitude must be between -180 and 180.', field='longitude')
        code = payload.get('country_code')
        if code and (not ValidationHelper.is_missing(code)):
            country = self.env['res.country'].search([('code', '=', str(code).upper().strip())], limit=1)
            if not country:
                result.add(f"country_code '{code}' is not a recognised ISO country code.", field='country_code')
        return result

    @api.model
    def create_address(self, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        clean = self._whitelist(payload, _ADDRESS_FIELDS)
        vr = self._validate_payload(clean)
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))
        country = self._resolve_country(clean.get('country_code'))
        if not country:
            raise ValidationError('country_code is required.')
        existing = self.env['jabin.user.address'].search_count([('user_id', '=', user_id)])
        is_default = clean.get('is_default', False) if existing else True
        vals = self._map_vals(clean, country_id=country.id)
        vals['user_id'] = user_id
        vals['is_default'] = bool(is_default)
        addr = self.env['jabin.user.address'].create(vals)
        _logger.audit('Address created: id=%s user=%s', addr.id, user_id, extra={'address_id': addr.id, 'user_id': user_id, 'action': 'create_address'})
        return addr.to_public_dict()

    @api.model
    def get_address(self, address_id: int, user_id: int) -> Dict[str, Any]:
        addr = self.env['jabin.user.address'].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f'Address {address_id} not found for user {user_id}.')
        return addr.to_public_dict()

    @api.model
    def list_addresses(self, user_id: int, page: int=1, per_page: int=20) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        domain = [('user_id', '=', user_id)]
        Addr = self.env['jabin.user.address']
        total = Addr.search_count(domain)
        meta = PaginationHelper.meta_dict(total, page, per_page)
        (offset, limit) = PaginationHelper.offset_limit(page, per_page)
        addresses = Addr.search(domain, offset=offset, limit=limit)
        return ([a.to_public_dict() for a in addresses], meta)

    @api.model
    def update_address(self, address_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        addr = self.env['jabin.user.address'].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f'Address {address_id} not found for user {user_id}.')
        clean = self._whitelist(payload, _ADDRESS_FIELDS)
        vr = self._validate_payload(clean, is_update=True)
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))
        vals = self._map_vals(clean, country_id=self._resolve_country(clean.get('country_code')))
        if vals:
            addr.write(vals)
            _logger.audit('Address updated: id=%s user=%s fields=%s', addr.id, user_id, list(vals.keys()), extra={'address_id': addr.id, 'user_id': user_id, 'action': 'update_address'})
        return addr.to_public_dict()

    @api.model
    def delete_address(self, address_id: int, user_id: int) -> Dict[str, Any]:
        addr = self.env['jabin.user.address'].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f'Address {address_id} not found for user {user_id}.')
        was_default = addr.is_default
        addr.unlink()
        _logger.audit('Address deleted: id=%s user=%s', address_id, user_id, extra={'address_id': address_id, 'user_id': user_id, 'action': 'delete_address'})
        if was_default:
            next_addr = self.env['jabin.user.address'].search([('user_id', '=', user_id)], order='id desc', limit=1)
            if next_addr:
                next_addr.write({'is_default': True})
        return {'id': address_id, 'deleted': True}

    @api.model
    def set_default(self, address_id: int, user_id: int) -> Dict[str, Any]:
        addr = self.env['jabin.user.address'].find_owned(address_id, user_id)
        if not addr:
            raise MissingError(f'Address {address_id} not found for user {user_id}.')
        addr.write({'is_default': True})
        _logger.audit('Address set default: id=%s user=%s', addr.id, user_id, extra={'address_id': addr.id, 'user_id': user_id, 'action': 'set_default'})
        return {'id': addr.id, 'is_default': True}

    @staticmethod
    def _whitelist(payload: Dict[str, Any], allowed: set) -> Dict[str, Any]:
        return {k: v for (k, v) in payload.items() if k in allowed}

    @api.model
    def _resolve_country(self, code: Optional[str]):
        if not code or ValidationHelper.is_missing(code):
            return self.env['res.country']
        return self.env['res.country'].search([('code', '=', str(code).upper().strip())], limit=1)

    @staticmethod
    def _map_vals(clean: Dict[str, Any], country_id: Optional[int]=None) -> Dict[str, Any]:
        vals: Dict[str, Any] = {}
        if 'title' in clean and (not ValidationHelper.is_missing(clean['title'])):
            vals['title'] = clean['title']
        if 'recipient_name' in clean and (not ValidationHelper.is_missing(clean['recipient_name'])):
            vals['recipient_name'] = clean['recipient_name']
        if 'recipient_phone' in clean:
            if ValidationHelper.is_missing(clean['recipient_phone']):
                vals['x_recipient_phone'] = False
            else:
                vals['x_recipient_phone'] = PhoneValidator.normalise(clean['recipient_phone'])
        if country_id:
            vals['country_id'] = country_id
        if 'city' in clean and (not ValidationHelper.is_missing(clean['city'])):
            vals['city'] = clean['city']
        if 'district' in clean:
            vals['district'] = clean['district'] or False
        if 'street' in clean and (not ValidationHelper.is_missing(clean['street'])):
            vals['street'] = clean['street']
        if 'building' in clean:
            vals['building'] = clean['building'] or False
        if 'floor' in clean:
            vals['floor'] = clean['floor'] or False
        if 'apartment' in clean:
            vals['apartment'] = clean['apartment'] or False
        if 'latitude' in clean and (not ValidationHelper.is_missing(clean.get('latitude'))):
            vals['latitude'] = float(clean['latitude'])
        if 'longitude' in clean and (not ValidationHelper.is_missing(clean.get('longitude'))):
            vals['longitude'] = float(clean['longitude'])
        if 'is_default' in clean:
            vals['is_default'] = bool(clean['is_default'])
        return vals