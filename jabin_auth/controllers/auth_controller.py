from __future__ import annotations
from typing import Any
from odoo import http
from odoo.addons.jabin_core import ResponseBuilder
from odoo.addons.jabin_security import auth_required
from odoo.addons.jabin_security.utils.security_context import SecurityContext
from odoo.addons.jabin_api.controllers.base import BaseApiController


class AuthController(BaseApiController):

    @http.route('/api/v1/auth/login', methods=['POST'], type='http', auth='none', csrf=False)
    def login(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            login_value = payload.get('login') or payload.get('email')
            password = payload.get('password')
            if not login_value or not password:
                ctx.set_body(ResponseBuilder.validation_error(
                    [{'field': 'login', 'message': 'login (email or phone) is required.'} if not login_value else {
                        'field': 'password', 'message': 'password is required.'}]), status=400)
            else:
                svc = http.request.env['jabin.auth.service']
                result = svc.login(login_value, password)
                ctx.set_body(ResponseBuilder.success(data=result, message='Login successful'))
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
                svc = http.request.env['jabin.auth.service']
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
                svc = http.request.env['jabin.auth.service']
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
                svc = http.request.env['jabin.auth.service']
                result = svc.verify(token)
                ctx.set_body(ResponseBuilder.success(data=result, message='Token is valid'))
        return ctx.response

    @http.route('/api/v1/auth/profile', methods=['GET'], type='http', auth='none', csrf=False)
    @auth_required
    def get_profile(self, **kwargs: Any):
        with self.handle() as ctx:
            sec_ctx = SecurityContext.get()
            svc = http.request.env['jabin.auth.service']
            profile = svc.get_profile(sec_ctx.user_id)
            ctx.set_body(ResponseBuilder.success(data=profile, message='Profile retrieved successfully'))
        return ctx.response

    @http.route('/api/v1/auth/profile', methods=['PUT'], type='http', auth='none', csrf=False)
    @auth_required
    def update_profile(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            sec_ctx = SecurityContext.get()
            svc = http.request.env['jabin.auth.service']
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
                svc = http.request.env['jabin.auth.service']
                result = svc.change_password(sec_ctx.user_id, current, new)
                ctx.set_body(ResponseBuilder.success(data=result, message='Password changed successfully'))
        return ctx.response
