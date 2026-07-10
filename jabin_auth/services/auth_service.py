from __future__ import annotations
from typing import Any, Dict, Optional
from odoo import api, fields, models
from odoo.exceptions import MissingError, ValidationError
from odoo.addons.jabin_core import EmailValidator, JabinLogger, ValidationHelper
from odoo.addons.jabin_security.utils.jwt_utils import JWTError, JWTUtils
from odoo.addons.jabin_security.utils.security_context import SecurityContext

_logger = JabinLogger.get('auth.service')
_PROFILE_UPDATE_FIELDS = {'name', 'phone', 'avatar'}

class AuthService(models.AbstractModel):
    _name = 'jabin.auth.service'
    _description = 'JABIN Auth Service'

    # =========================================================================
    # EXISTING METHODS (Modified for OTP compatibility)
    # =========================================================================

    @api.model
    def login(self, login: str, password: str) -> Dict[str, Any]:
        """Legacy password-based login. Kept for backward compatibility."""
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

        _logger.audit('User logged in: id=%s type=%s', user_id, user_type,
                      extra={'user_id': user_id, 'action': 'login_success'})
        return {'user': user.to_public_dict(), 'tokens': tokens}

    @api.model
    def login_with_otp(self, email: str) -> str:
        """New: Send login OTP to existing user."""
        if not email:
            raise ValidationError('Email is required.')

        email = email.strip().lower()

        # ✅ FIXED: Added .sudo()
        User = self.env['res.users'].sudo()
        user = User.find_by_login(email)

        if not user:
            _logger.audit('Login OTP failed: user not found for email=%s', email,
                          extra={'email': email, 'action': 'login_otp_no_user'})
            return "Verification code sent successfully"

        status = getattr(user, 'x_status', None)
        if status not in ('active',):
            _logger.audit('Login OTP blocked: user=%s status=%s', user.id, status,
                          extra={'user_id': user.id, 'action': 'login_otp_blocked_status'})
            if status == 'pending':
                return self._send_registration_otp(email, user.id)
            raise ValidationError('Account is not active. Please contact support.')

        otp_service = self.env['jabin.otp.service']
        plain_code = otp_service.create_and_send_otp(
            email=email,
            purpose='login',
            user_id=user.id
        )

        try:
            self.env['jabin.audit.service'].log_login(user_id=user.id, success=True, login=email)
        except Exception:
            pass

        _logger.audit('Login OTP sent: user=%s email=%s', user.id, email,
                      extra={'user_id': user.id, 'action': 'login_otp_sent'})
        return "Verification code sent successfully"

    @api.model
    def verify_login_otp(self, email: str, code: str) -> Dict[str, Any]:
        """Verify login OTP and return tokens."""
        if not email or not code:
            raise ValidationError('Email and verification code are required.')

        email = email.strip().lower()

        otp_service = self.env['jabin.otp.service']
        if not otp_service.verify_otp(email, code, 'login'):
            try:
                # ✅ FIXED: Added .sudo()
                user = self.env['res.users'].sudo().find_by_login(email)
                user_id = user.id if user else None
                self.env['jabin.audit.service'].log_login(user_id=user_id, success=False, login=email)
            except Exception:
                pass

            _logger.audit('Login OTP verification failed: email=%s', email,
                          extra={'email': email, 'action': 'login_otp_verify_failed'})
            raise ValidationError('Invalid verification code.')

        # ✅ FIXED: Added .sudo()
        User = self.env['res.users'].sudo()
        user = User.find_by_login(email)

        if not user:
            raise ValidationError('User not found.')

        status = getattr(user, 'x_status', None)
        if status != 'active':
            raise ValidationError('Account is not active.')

        user_type = getattr(user, 'x_user_type', None) or 'customer'
        tokens = self.env['jabin.token.service'].issue_pair(user.id, user_type, email)

        try:
            user.sudo().write({'x_last_login': fields.Datetime.now()})
        except Exception:
            pass

        try:
            self.env['jabin.audit.service'].log_login(user_id=user.id, success=True, login=email)
        except Exception:
            pass

        _logger.audit('User logged in via OTP: id=%s type=%s', user.id, user_type,
                      extra={'user_id': user.id, 'action': 'login_otp_success'})

        return {
            'success': True,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': 'Bearer'
        }

    @api.model
    def register(self, email: str) -> str:
        """Register a new user with email only."""
        if not email:
            raise ValidationError('Email is required.')

        vr = EmailValidator.validate(email, field='email')
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))

        email = email.strip().lower()

        # ✅ FIXED: Added .sudo()
        User = self.env['res.users'].sudo()
        existing_user = User.find_by_login(email)

        if existing_user:
            status = getattr(existing_user, 'x_status', None)
            if status == 'active':
                raise ValidationError('Email already registered and verified.')
            elif status == 'pending':
                return self._send_registration_otp(email, existing_user.id)
            else:
                pass

        user_type = 'customer'
        user_data = {
            'login': email,
            'name': email,
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
            'x_user_type': user_type,
            'x_status': 'pending',
            'password': '',
        }

        try:
            user = User.create(user_data)
            _logger.audit('User created (pending): id=%s email=%s', user.id, email,
                          extra={'user_id': user.id, 'email': email, 'action': 'user_created_pending'})
        except Exception as exc:
            _logger.error('Failed to create user: %s', exc)
            raise ValidationError(f'Failed to create user: {exc}')

        return self._send_registration_otp(email, user.id)

    @api.model
    def _send_registration_otp(self, email: str, user_id: int) -> str:
        """Send registration OTP to user."""
        otp_service = self.env['jabin.otp.service']
        plain_code = otp_service.create_and_send_otp(
            email=email,
            purpose='register',
            user_id=user_id
        )

        _logger.audit('Registration OTP sent: user=%s email=%s', user_id, email,
                      extra={'user_id': user_id, 'email': email, 'action': 'registration_otp_sent'})
        return "Verification code sent successfully"

    @api.model
    def verify_registration_otp(self, email: str, code: str) -> Dict[str, Any]:
        """Verify registration OTP and activate user account."""
        if not email or not code:
            raise ValidationError('Email and verification code are required.')

        email = email.strip().lower()

        otp_service = self.env['jabin.otp.service']
        if not otp_service.verify_otp(email, code, 'register'):
            _logger.audit('Registration OTP verification failed: email=%s', email,
                          extra={'email': email, 'action': 'registration_otp_verify_failed'})
            raise ValidationError('Invalid verification code.')

        # ✅ FIXED: Added .sudo()
        User = self.env['res.users'].sudo()
        user = User.find_by_login(email)

        if not user:
            raise ValidationError('User not found.')

        try:
            user.sudo().write({'x_status': 'active'})
            _logger.audit('User activated: id=%s email=%s', user.id, email,
                          extra={'user_id': user.id, 'email': email, 'action': 'user_activated'})
        except Exception as exc:
            _logger.error('Failed to activate user: %s', exc)
            raise ValidationError(f'Failed to activate user: {exc}')

        user_type = getattr(user, 'x_user_type', None) or 'customer'
        tokens = self.env['jabin.token.service'].issue_pair(user.id, user_type, email)

        try:
            user.sudo().write({'x_last_login': fields.Datetime.now()})
        except Exception:
            pass

        try:
            email_service = self.env['jabin.email.service']
            email_service.send_welcome_email(email, user.name)
        except Exception as exc:
            _logger.warning('Failed to send welcome email: %s', exc)

        try:
            self.env['jabin.audit.service'].log_login(user_id=user.id, success=True, login=email)
        except Exception:
            pass

        _logger.audit('User registered and verified via OTP: id=%s type=%s', user.id, user_type,
                      extra={'user_id': user.id, 'action': 'registration_otp_success'})

        return {
            'success': True,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': 'Bearer'
        }

    @api.model
    def resend_registration_otp(self, email: str) -> Dict[str, Any]:
        """Resend registration OTP to user."""
        if not email:
            return {'success': False, 'message': 'Email is required.'}

        email = email.strip().lower()

        # ✅ FIXED: Added .sudo()
        User = self.env['res.users'].sudo()
        user = User.find_by_login(email)

        if not user:
            return {'success': False, 'message': 'User not found.'}

        status = getattr(user, 'x_status', None)
        if status == 'active':
            return {'success': False, 'message': 'User already verified.'}

        otp_service = self.env['jabin.otp.service']
        can_resend, reason = otp_service.can_resend_otp(email, 'register')

        if not can_resend:
            return {'success': False, 'message': reason}

        success, message = otp_service.resend_otp(email, 'register', user.id)

        if success:
            _logger.audit('Registration OTP resent: user=%s email=%s', user.id, email,
                          extra={'user_id': user.id, 'email': email, 'action': 'registration_otp_resent'})

        return {'success': success, 'message': message}

    @api.model
    def resend_login_otp(self, email: str) -> Dict[str, Any]:
        """Resend login OTP to user."""
        if not email:
            return {'success': False, 'message': 'Email is required.'}

        email = email.strip().lower()

        # ✅ FIXED: Added .sudo()
        User = self.env['res.users'].sudo()
        user = User.find_by_login(email)

        if not user:
            return {'success': True, 'message': 'Verification code sent successfully'}

        status = getattr(user, 'x_status', None)
        if status != 'active':
            return {'success': False, 'message': 'Account is not active.'}

        otp_service = self.env['jabin.otp.service']
        can_resend, reason = otp_service.can_resend_otp(email, 'login')

        if not can_resend:
            return {'success': False, 'message': reason}

        success, message = otp_service.resend_otp(email, 'login', user.id)

        if success:
            _logger.audit('Login OTP resent: user=%s email=%s', user.id, email,
                          extra={'user_id': user.id, 'email': email, 'action': 'login_otp_resent'})

        return {'success': success, 'message': message}

    @api.model
    def logout(self, refresh_token: str, user_id: Optional[int] = None) -> Dict[str, Any]:
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
        return {
            'valid': True,
            'user_id': JWTUtils.get_user_id(claims),
            'user_type': JWTUtils.get_user_type(claims),
            'email': JWTUtils.get_email(claims),
            'expires_at': claims.get('exp')
        }

    @api.model
    def get_profile(self, user_id: int) -> Dict[str, Any]:
        # ✅ FIXED: Added .sudo()
        user = self.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            raise MissingError('User not found.')

        profile_data = user.to_public_dict()
        profile_completion_svc = self.env['jabin.profile.completion.service']
        profile_status = profile_completion_svc.get_profile_status(user_id)
        profile_data['profile_completion'] = profile_status
        return profile_data

    @api.model
    def update_profile(self, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        # ✅ FIXED: Added .sudo()
        user = self.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            raise MissingError('User not found.')

        clean = {k: v for (k, v) in payload.items() if
                 k in _PROFILE_UPDATE_FIELDS and (not ValidationHelper.is_missing(v))}

        if 'phone' in clean:
            from odoo.addons.jabin_core import PhoneValidator
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
            _logger.audit('Profile updated (self): user=%s fields=%s', user_id, list(vals.keys()),
                          extra={'user_id': user_id, 'action': 'profile_update'})

        profile_completion_svc = self.env['jabin.profile.completion.service']
        if profile_completion_svc.is_profile_completed(user_id):
            try:
                user.sudo().write({'x_profile_completed': True})
            except Exception:
                pass

        return user.to_public_dict()

    @api.model
    def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, Any]:
        # ✅ FIXED: Added .sudo()
        user = self.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            raise MissingError('User not found.')
        if not current_password or not new_password:
            raise ValidationError('Current password and new password are required.')

        verified = self.env['jabin.password.service'].authenticate(user.login, current_password)
        if verified is None:
            raise ValidationError('Current password is incorrect.')

        from odoo.addons.jabin_core import PasswordValidator
        vr = PasswordValidator.validate(new_password, field='new_password')
        if not vr.ok:
            raise ValidationError('\n'.join((e.message for e in vr.errors)))

        self.env['jabin.password.service'].set_user_password(user_id, new_password)
        return {'password_changed': True}