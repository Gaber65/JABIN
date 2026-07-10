from __future__ import annotations
from typing import Any, Dict, Optional
from odoo import api, fields, models
from odoo.exceptions import MissingError, ValidationError
from odoo.addons.jabin_core import EmailValidator, JabinLogger, PasswordValidator, PhoneValidator, ValidationHelper, ValidationResult
from odoo.addons.jabin_security.utils.jwt_utils import JWTError, JWTUtils
from odoo.addons.jabin_security.utils.security_context import SecurityContext
_logger = JabinLogger.get('auth.service')
_PROFILE_UPDATE_FIELDS = {'name', 'phone', 'avatar'}

class AuthService(models.AbstractModel):
    _name = 'jabin.auth.service'
    _description = 'JABIN Auth Service'

    @api.model
    def login(self, login: str, password: str) -> Dict[str, Any]:
        if not login or not password:
            raise ValidationError('Login and password are required.')
        user_id = self.env['jabin.password.service'].authenticate(login, password)
        if user_id is None:
            try:
                self.env['jabin.audit.service'].log_login(user_id=None, success=False, login=login)
            except Exception:
                pass
            raise ValidationError('Invalid login credentials.')
        user = self.env['res.users'].browse(user_id)
        user_type = getattr(user, 'x_user_type', None) or 'customer'
        email = user.login or ''
        tokens = self.env['jabin.token.service'].issue_pair(user_id, user_type, email)
        try:
            user.sudo().write({'x_last_login': fields.Datetime.now()})
        except Exception:
            pass
        try:
            self.env['jabin.audit.service'].log_login(user_id, success=True)
        except Exception:
            pass
        _logger.audit('User logged in: id=%s type=%s', user_id, user_type, extra={'user_id': user_id, 'action': 'login_success'})
        return {'user': user.to_public_dict(), 'tokens': tokens}

    @api.model
    def logout(self, refresh_token: str, user_id: Optional[int]=None) -> Dict[str, Any]:
        self.env['jabin.token.service'].revoke_refresh_token(refresh_token)
        try:
            self.env['jabin.audit.service'].log_logout(user_id or 0)
        except Exception:
            pass
        return {'logged_out': True}

    @api.model
    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        tokens = self.env['jabin.token.service'].refresh(refresh_token)
        return {'tokens': tokens}

    @api.model
    def verify(self, access_token: str) -> Dict[str, Any]:
        if not access_token:
            raise JWTError('Access token is required.')
        claims = self.env['jabin.token.service'].verify_access_token(access_token)
        return {'valid': True, 'user_id': JWTUtils.get_user_id(claims), 'user_type': JWTUtils.get_user_type(claims), 'email': JWTUtils.get_email(claims), 'expires_at': claims.get('exp')}

    @api.model
    def get_profile(self, user_id: int) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError('User not found.')
        return user.to_public_dict()

    @api.model
    def update_profile(self, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError('User not found.')
        clean = {k: v for (k, v) in payload.items() if k in _PROFILE_UPDATE_FIELDS and (not ValidationHelper.is_missing(v))}
        if 'phone' in clean:
            vr = PhoneValidator.validate(clean['phone'], field='phone')
            if not vr.ok:
                raise ValidationError('\n'.join((e.message for e in vr.errors)))
            clean['x_phone'] = PhoneValidator.normalise(clean.pop('phone'))
        vals: Dict[str, Any] = {}
        if 'name' in clean:
            vals['name'] = clean['name']
        if 'x_phone' in clean:
            vals['x_phone'] = clean['x_phone']
        if 'avatar' in clean:
            vals['x_avatar'] = clean['avatar']
        if vals:
            user.sudo().write(vals)
            _logger.audit('Profile updated (self): user=%s fields=%s', user_id, list(vals.keys()), extra={'user_id': user_id, 'action': 'profile_update'})
        return user.to_public_dict()

    @api.model
    def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, Any]:
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise MissingError('User not found.')
        if not current_password or not new_password:
            raise ValidationError('Current password and new password are required.')
        verified = self.env['jabin.password.service'].authenticate(user.login, current_password)
        if verified is None:
            raise ValidationError('Current password is incorrect.')
        vr = PasswordValidator.validate(new_password, field='new_password')
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))
        self.env['jabin.password.service'].set_user_password(user_id, new_password)
        return {'password_changed': True}