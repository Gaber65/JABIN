from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from odoo import api, fields, models
from odoo.exceptions import MissingError, ValidationError
from odoo.addons.jabin_core import EmailValidator, JabinLogger, PaginationHelper, PasswordValidator, PhoneValidator, ResponseBuilder, ValidationResult, ValidationHelper
from odoo.addons.jabin_core.constants.user_types import UserType
_logger = JabinLogger.get('users.service')
_USER_CREATE_FIELDS = {
    'name',
    'email',
    'login',
    'phone',
    'user_type',
    'password',
    'status',
    'avatar'
}
_USER_UPDATE_FIELDS = {'name', 'phone', 'user_type', 'status', 'avatar'}

class UserService(models.AbstractModel):
    _name = 'jabin.user.service'
    _description = 'JABIN User Service'

    @api.model
    def _validate_create_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        result.require('name', payload.get('name'))
        result.require('email', payload.get('email'))
        result.require('password', payload.get('password'))
        email = payload.get('email')
        if email and (not ValidationHelper.is_missing(email)):
            result.merge(EmailValidator.validate(email, field='email'))
        password = payload.get('password')
        if password and (not ValidationHelper.is_missing(password)):
            result.merge(PasswordValidator.validate(password, field='password'))
        phone = payload.get('phone')
        if phone and (not ValidationHelper.is_missing(phone)):
            result.merge(PhoneValidator.validate(phone, field='phone'))
        user_type = payload.get('user_type')
        if user_type and (not ValidationHelper.is_missing(user_type)):
            if not UserType.has_value(str(user_type)):
                result.add(f'user_type must be one of {UserType.all_values()}.', field='user_type')
        status = payload.get('status')
        if status and (not ValidationHelper.is_missing(status)):
            valid_statuses = {'active', 'suspended', 'pending', 'inactive'}
            if status not in valid_statuses:
                result.add(f'status must be one of {sorted(valid_statuses)}.', field='status')
        return result

    @api.model
    def _validate_update_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        email = payload.get('email')
        if email and (not ValidationHelper.is_missing(email)):
            result.merge(EmailValidator.validate(email, field='email'))
        phone = payload.get('phone')
        if phone and (not ValidationHelper.is_missing(phone)):
            result.merge(PhoneValidator.validate(phone, field='phone'))
        user_type = payload.get('user_type')
        if user_type and (not ValidationHelper.is_missing(user_type)):
            if not UserType.has_value(str(user_type)):
                result.add(f'user_type must be one of {UserType.all_values()}.', field='user_type')
        status = payload.get('status')
        if status and (not ValidationHelper.is_missing(status)):
            valid_statuses = {'active', 'suspended', 'pending', 'inactive'}
            if status not in valid_statuses:
                result.add(f'status must be one of {sorted(valid_statuses)}.', field='status')
        password = payload.get('password')
        if password and (not ValidationHelper.is_missing(password)):
            result.merge(PasswordValidator.validate(password, field='password'))
        return result

    @api.model
    def _check_uniqueness(self, email: Optional[str], phone: Optional[str], exclude_user_id: Optional[int]=None) -> ValidationResult:
        result = ValidationResult()
        User = self.env['res.users']
        if email and (not ValidationHelper.is_missing(email)):
            existing = User.find_by_login(email)
            if existing and (exclude_user_id is None or existing.id != exclude_user_id):
                result.add('A user with this email already exists.', field='email')
        if phone and (not ValidationHelper.is_missing(phone)):
            existing = User.find_by_phone(phone)
            if existing and (exclude_user_id is None or existing.id != exclude_user_id):
                result.add('A user with this phone already exists.', field='phone')
        return result

    @api.model
    def create_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        clean = self._whitelist(payload, _USER_CREATE_FIELDS)
        vr = self._validate_create_payload(clean)
        vr.merge(self._check_uniqueness(clean.get('email'), clean.get('phone')))
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))
        vals = self._map_create_vals(clean)
        _logger.info("CREATE USER VALS => %s", vals)

        user = self.env['res.users'].sudo().create(vals)
        _logger.audit('User created via service: id=%s email=%s type=%s', user.id, user.login, user.x_user_type, extra={'user_id': user.id, 'action': 'create_user'})
        return user.to_public_dict()

    @api.model
    def get_user(self, user_id: int) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError(f'User {user_id} not found.')
        return user.to_public_dict()

    @api.model
    def list_users(self, page: int=1, per_page: int=20, user_type: Optional[str]=None, status: Optional[str]=None, search: Optional[str]=None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        domain: List[Tuple[str, str, Any]] = []
        if user_type:
            domain.append(('x_user_type', '=', user_type))
        if status:
            domain.append(('x_status', '=', status))
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('login', 'ilike', search))
        User = self.env['res.users']
        total = User.search_count(domain)
        meta = PaginationHelper.meta_dict(total, page, per_page)
        (offset, limit) = PaginationHelper.offset_limit(page, per_page)
        users = User.search(domain, offset=offset, limit=limit, order='id desc')
        return ([u.to_public_dict() for u in users], meta)

    @api.model
    def update_user(self, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError(f'User {user_id} not found.')
        clean = self._whitelist(payload, _USER_UPDATE_FIELDS | {'email', 'password'})
        vr = self._validate_update_payload(clean)
        vr.merge(self._check_uniqueness(clean.get('email'), clean.get('phone'), exclude_user_id=user.id))
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))
        vals = self._map_update_vals(clean)
        if vals:
            user.write(vals)
            _logger.audit('User updated via service: id=%s fields=%s', user.id, list(vals.keys()), extra={'user_id': user.id, 'action': 'update_user'})
        return user.to_public_dict()

    @api.model
    def archive_user(self, user_id: int) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError(f'User {user_id} not found.')
        user.write({'active': False, 'x_status': 'inactive'})
        _logger.audit('User archived: id=%s', user.id, extra={'user_id': user.id, 'action': 'archive_user'})
        return {'id': user.id, 'active': False, 'status': user.x_status}

    @api.model
    def restore_user(self, user_id: int) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError(f'User {user_id} not found.')
        user.write({'active': True, 'x_status': 'active'})
        _logger.audit('User restored: id=%s', user.id, extra={'user_id': user.id, 'action': 'restore_user'})
        return {'id': user.id, 'active': True, 'status': user.x_status}

    @api.model
    def set_status(self, user_id: int, status: str) -> Dict[str, Any]:
        valid = {'active', 'suspended', 'pending', 'inactive'}
        if status not in valid:
            raise ValidationError(f'status must be one of {sorted(valid)}.')
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError(f'User {user_id} not found.')
        user.write({'x_status': status})
        _logger.audit('User status changed: id=%s status=%s', user.id, status, extra={'user_id': user.id, 'action': 'set_status', 'new_status': status})
        return {'id': user.id, 'status': user.x_status}

    @staticmethod
    def _whitelist(payload: Dict[str, Any], allowed: set) -> Dict[str, Any]:
        return {k: v for (k, v) in payload.items() if k in allowed}

    def _map_create_vals(self, clean: Dict[str, Any]) -> Dict[str, Any]:
        vals: Dict[str, Any] = {}

        # Default company for public API creation
        company = self.env['res.company'].sudo().search([], limit=1)
        vals['company_id'] = company.id if company else False

        if 'name' in clean:
            vals['name'] = clean['name']

        if 'email' in clean:
            vals['login'] = EmailValidator.normalise(clean['email'])

        if 'phone' in clean and not ValidationHelper.is_missing(clean['phone']):
            vals['x_phone'] = PhoneValidator.normalise(clean['phone'])

        if 'user_type' in clean and not ValidationHelper.is_missing(clean['user_type']):
            vals['x_user_type'] = clean['user_type']
        else:
            vals['x_user_type'] = UserType.CUSTOMER.value

        if 'status' in clean and not ValidationHelper.is_missing(clean['status']):
            vals['x_status'] = clean['status']
        else:
            vals['x_status'] = 'pending'

        if 'password' in clean and not ValidationHelper.is_missing(clean['password']):
            vals['password'] = clean['password']

        if 'avatar' in clean and not ValidationHelper.is_missing(clean['avatar']):
            vals['x_avatar'] = clean['avatar']

        return vals
    @staticmethod
    def _map_update_vals(clean: Dict[str, Any]) -> Dict[str, Any]:
        vals: Dict[str, Any] = {}
        if 'name' in clean and (not ValidationHelper.is_missing(clean['name'])):
            vals['name'] = clean['name']
        if 'email' in clean and (not ValidationHelper.is_missing(clean['email'])):
            login = EmailValidator.normalise(clean['email'])
            vals['login'] = login
            vals['email'] = login
        if 'phone' in clean:
            if ValidationHelper.is_missing(clean['phone']):
                vals['x_phone'] = False
            else:
                vals['x_phone'] = PhoneValidator.normalise(clean['phone'])
        if 'user_type' in clean and (not ValidationHelper.is_missing(clean['user_type'])):
            vals['x_user_type'] = clean['user_type']
        if 'status' in clean and (not ValidationHelper.is_missing(clean['status'])):
            vals['x_status'] = clean['status']
        if 'password' in clean and (not ValidationHelper.is_missing(clean['password'])):
            vals['password'] = clean['password']
        if 'avatar' in clean:
            if ValidationHelper.is_missing(clean['avatar']):
                vals['x_avatar'] = False
            else:
                vals['x_avatar'] = clean['avatar']
        return vals