from __future__ import annotations
from typing import Any
from odoo import http
from odoo.addons.jabin_core import ResponseBuilder
from odoo.addons.jabin_security import auth_required
from odoo.addons.jabin_security.utils.security_context import SecurityContext
from odoo.addons.jabin_api.controllers.base import BaseApiController


class AuthController(BaseApiController):

    # =========================================================================
    # EXISTING ENDPOINTS (Modified for OTP compatibility)
    # =========================================================================

    @http.route('/api/v1/auth/login', methods=['POST'], type='http', auth='none', csrf=False)
    def login(self, **kwargs: Any):
        """Handle both password-based and passwordless login."""
        with self.handle() as ctx:
            payload = self.parse_json_body()
            login_value = payload.get('login') or payload.get('email')
            password = payload.get('password')

            if not login_value:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'login', 'message': 'login (email) is required.'}]), status=400)
                return ctx.response

            # FIX: Always use sudo() for service calls from anonymous endpoints
            svc = http.request.env['jabin.auth.service'].sudo()

            if password:
                # LEGACY: Password-based login (keep for backward compatibility)
                result = svc.login(login_value, password)
                ctx.set_body(ResponseBuilder.success(data=result, message='Login successful'))
            else:
                # NEW: Passwordless login - send OTP
                result = svc.login_with_otp(login_value)
                ctx.set_body(ResponseBuilder.success(
                    data={'message': result},
                    message='Verification code sent successfully'
                ))
        return ctx.response

    @http.route('/api/v1/auth/logout', methods=['POST'], type='http', auth='none', csrf=False)
    @auth_required
    def logout(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            refresh_token = payload.get('refresh_token')
            if not refresh_token:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'refresh_token', 'message': 'refresh_token is required.'}]), status=400)
            else:
                sec_ctx = SecurityContext.get()
                # FIX: Use sudo() for service call
                svc = http.request.env['jabin.auth.service'].sudo()
                result = svc.logout(refresh_token, user_id=sec_ctx.user_id)
                ctx.set_body(ResponseBuilder.success(data=result, message='Logout successful'))
        return ctx.response

    @http.route('/api/v1/auth/refresh', methods=['POST'], type='http', auth='none', csrf=False)
    def refresh(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            refresh_token = payload.get('refresh_token')
            if not refresh_token:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'refresh_token', 'message': 'refresh_token is required.'}]), status=400)
            else:
                # FIX: Use sudo() for service call
                svc = http.request.env['jabin.auth.service'].sudo()
                result = svc.refresh(refresh_token)
                ctx.set_body(ResponseBuilder.success(data=result, message='Token refreshed successfully'))
        return ctx.response

    @http.route('/api/v1/auth/verify', methods=['GET'], type='http', auth='none', csrf=False)
    def verify(self, **kwargs: Any):
        with self.handle() as ctx:
            raw_header = ''
            try:
                raw_header = http.request.httprequest.headers.get('Authorization', '')
            except Exception:
                pass
            token = ''
            if raw_header:
                parts = raw_header.split(None, 1)
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1].strip()
            if not token:
                ctx.set_body(ResponseBuilder.unauthorized(message='Access token required in Authorization header.'),
                             status=401)
            else:
                # FIX: Use sudo() for service call
                svc = http.request.env['jabin.auth.service'].sudo()
                result = svc.verify(token)
                ctx.set_body(ResponseBuilder.success(data=result, message='Token is valid'))
        return ctx.response

    @http.route('/api/v1/auth/profile', methods=['GET'], type='http', auth='none', csrf=False)
    @auth_required
    def get_profile(self, **kwargs: Any):
        with self.handle() as ctx:
            sec_ctx = SecurityContext.get()
            svc = http.request.env['jabin.auth.service'].sudo()
            profile = svc.get_profile(sec_ctx.user_id)
            ctx.set_body(ResponseBuilder.success(data=profile, message='Profile retrieved successfully'))
        return ctx.response

    @http.route('/api/v1/auth/profile', methods=['PUT'], type='http', auth='none', csrf=False)
    @auth_required
    def update_profile(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            sec_ctx = SecurityContext.get()
            svc = http.request.env['jabin.auth.service'].sudo()
            profile = svc.update_profile(sec_ctx.user_id, payload)
            ctx.set_body(ResponseBuilder.success(data=profile, message='Profile updated successfully'))
        return ctx.response

    @http.route('/api/v1/auth/change-password', methods=['POST'], type='http', auth='none', csrf=False)
    @auth_required
    def change_password(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            current = payload.get('current_password')
            new = payload.get('new_password')
            if not current or not new:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'current_password', 'message': 'current_password is required.'} if not current else {
                        'field': 'new_password', 'message': 'new_password is required.'}]), status=400)
            else:
                sec_ctx = SecurityContext.get()
                svc = http.request.env['jabin.auth.service'].sudo()
                result = svc.change_password(sec_ctx.user_id, current, new)
                ctx.set_body(ResponseBuilder.success(data=result, message='Password changed successfully'))
        return ctx.response

    # =========================================================================
    # NEW OTP ENDPOINTS
    # =========================================================================

    @http.route('/api/v1/auth/register', methods=['POST'], type='http', auth='none', csrf=False)
    def register(self, **kwargs: Any):
        """Register a new user with email only. Sends verification OTP."""
        with self.handle() as ctx:
            payload = self.parse_json_body()
            email = payload.get('email')

            if not email:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'email', 'message': 'email is required.'}]), status=400)
                return ctx.response

            # Validate email format
            from odoo.addons.jabin_core import EmailValidator
            vr = EmailValidator.validate(email, field='email')
            if not vr.ok:
                errors = [{'field': err.field, 'message': err.message} for err in vr.errors]
                ctx.set_body(ResponseBuilder.validation_error(errors), status=400)
                return ctx.response

            # FIX: Use sudo() for service call
            svc = http.request.env['jabin.auth.service'].sudo()

            # Check if email already exists
            User = http.request.env['res.users'].sudo()
            existing_user = User.find_by_login(email)
            if existing_user:
                # Check if user is already active
                if existing_user.x_status == 'active':
                    ctx.set_body(ResponseBuilder.error(
                        message='Email already registered and verified',
                        code=409
                    ), status=409)
                    return ctx.response
                elif existing_user.x_status == 'pending':
                    # User exists but not verified - resend OTP
                    result = svc.resend_registration_otp(email)
                    ctx.set_body(ResponseBuilder.success(
                        data={'email': email, 'expires_in': 300},
                        message='Verification code resent successfully'
                    ))
                    return ctx.response

            # Create new user and send OTP
            result = svc.register(email)

            ctx.set_body(ResponseBuilder.success(
                data={'email': email, 'expires_in': 300},
                message='Verification code sent successfully'
            ))
        return ctx.response

    @http.route('/api/v1/auth/register/verify', methods=['POST'], type='http', auth='none', csrf=False)
    def verify_registration_otp(self, **kwargs: Any):
        """Verify the registration OTP and activate the user account."""
        with self.handle() as ctx:
            payload = self.parse_json_body()
            email = payload.get('email')
            code = payload.get('code')

            if not email:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'email', 'message': 'email is required.'}]), status=400)
                return ctx.response
            if not code:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'code', 'message': 'code is required.'}]), status=400)
                return ctx.response

            # FIX: Use sudo() for service call
            svc = http.request.env['jabin.auth.service'].sudo()
            result = svc.verify_registration_otp(email, code)

            if not result.get('success'):
                error_msg = result.get('message', 'Invalid verification code')
                ctx.set_body(ResponseBuilder.error(
                    message=error_msg,
                    code=401
                ), status=401)
                return ctx.response

            # Return tokens for automatic login
            ctx.set_body(ResponseBuilder.success(
                data={
                    'access_token': result['access_token'],
                    'refresh_token': result['refresh_token'],
                    'token_type': 'Bearer'
                },
                message='Account verified successfully'
            ))
        return ctx.response

    @http.route('/api/v1/auth/login/verify', methods=['POST'], type='http', auth='none', csrf=False)
    def verify_login_otp(self, **kwargs: Any):
        """Verify login OTP and return access tokens."""
        with self.handle() as ctx:
            payload = self.parse_json_body()
            email = payload.get('email')
            code = payload.get('code')

            if not email:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'email', 'message': 'email is required.'}]), status=400)
                return ctx.response
            if not code:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'code', 'message': 'code is required.'}]), status=400)
                return ctx.response

            # FIX: Use sudo() for service call
            svc = http.request.env['jabin.auth.service'].sudo()
            result = svc.verify_login_otp(email, code)

            if not result.get('success'):
                error_msg = result.get('message', 'Invalid verification code')
                ctx.set_body(ResponseBuilder.error(
                    message=error_msg,
                    code=401
                ), status=401)
                return ctx.response

            # Return tokens
            ctx.set_body(ResponseBuilder.success(
                data={
                    'access_token': result['access_token'],
                    'refresh_token': result['refresh_token'],
                    'token_type': 'Bearer'
                },
                message='Login successful'
            ))
        return ctx.response

    @http.route('/api/v1/auth/resend', methods=['POST'], type='http', auth='none', csrf=False)
    def resend_otp(self, **kwargs: Any):
        """Resend OTP for registration or login."""
        with self.handle() as ctx:
            payload = self.parse_json_body()
            email = payload.get('email')
            purpose = payload.get('purpose', 'register')  # Default to register

            if not email:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'email', 'message': 'email is required.'}]), status=400)
                return ctx.response

            # Validate email format
            from odoo.addons.jabin_core import EmailValidator
            vr = EmailValidator.validate(email, field='email')
            if not vr.ok:
                errors = [{'field': err.field, 'message': err.message} for err in vr.errors]
                ctx.set_body(ResponseBuilder.validation_error(errors), status=400)
                return ctx.response

            # FIX: Use sudo() for service call
            svc = http.request.env['jabin.auth.service'].sudo()

            if purpose == 'login':
                result = svc.resend_login_otp(email)
            else:
                result = svc.resend_registration_otp(email)

            if not result.get('success'):
                ctx.set_body(ResponseBuilder.error(
                    message=result.get('message', 'Failed to resend code'),
                    code=429
                ), status=429)
                return ctx.response

            ctx.set_body(ResponseBuilder.success(
                data={'email': email, 'expires_in': 300},
                message='Verification code resent successfully'
            ))
        return ctx.response

    @http.route('/api/v1/auth/otp/status', methods=['GET'], type='http', auth='none', csrf=False)
    def get_otp_status(self, **kwargs: Any):
        """Check the status of an OTP for an email and purpose."""
        with self.handle() as ctx:
            email = http.request.httprequest.args.get('email')
            purpose = http.request.httprequest.args.get('purpose', 'register')

            if not email:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'email', 'message': 'email is required.'}]), status=400)
                return ctx.response

            # FIX: Use sudo() for service call
            svc = http.request.env['jabin.otp.service'].sudo()
            status = svc.get_otp_status(email, purpose)

            ctx.set_body(ResponseBuilder.success(data=status))
        return ctx.response

    @http.route('/api/v1/auth/profile/status', methods=['GET'], type='http', auth='none', csrf=False)
    @auth_required
    def get_profile_status(self, **kwargs: Any):
        """Get profile completion status for the authenticated user."""
        with self.handle() as ctx:
            sec_ctx = SecurityContext.get()
            svc = http.request.env['jabin.profile.completion.service'].sudo()
            status = svc.get_profile_status(sec_ctx.user_id)

            ctx.set_body(ResponseBuilder.success(data=status))
        return ctx.response

    @http.route('/api/v1/auth/profile/check', methods=['POST'], type='http', auth='none', csrf=False)
    @auth_required
    def check_action_requirements(self, **kwargs: Any):
        """Check if user meets requirements for a specific action."""
        with self.handle() as ctx:
            payload = self.parse_json_body()
            action = payload.get('action')

            if not action:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'action', 'message': 'action is required.'}]), status=400)
                return ctx.response

            sec_ctx = SecurityContext.get()
            svc = http.request.env['jabin.profile.completion.service'].sudo()
            result = svc.check_requirements(sec_ctx.user_id, action)

            ctx.set_body(ResponseBuilder.success(data=result))
        return ctx.response