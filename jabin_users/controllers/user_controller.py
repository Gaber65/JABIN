from __future__ import annotations
from typing import Any
from odoo import http
from odoo.addons.jabin_core import ResponseBuilder, ValidationHelper
from odoo.addons.jabin_api.controllers.base import BaseApiController


class UserController(BaseApiController):

    @http.route('/api/v1/users', methods=['GET'], type='http', auth='none', csrf=False)
    def list_users(self, **kwargs: Any):
        with self.handle() as ctx:
            page = ValidationHelper.to_int(kwargs.get('page'), 1) or 1
            per_page = ValidationHelper.to_int(kwargs.get('per_page'), 20) or 20
            user_type = kwargs.get('user_type') or None
            status = kwargs.get('status') or None
            search = kwargs.get('search') or None
            svc = http.request.env['jabin.user.service']
            (data, meta) = svc.list_users(page=page, per_page=per_page, user_type=user_type, status=status,
                                          search=search)
            ctx.set_body(ResponseBuilder.success(data=data, meta=meta, message='Users retrieved successfully'))
        return ctx.response

    @http.route('/api/v1/users', methods=['POST'], type='http', auth='none', csrf=False)
    def create_user(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            svc = http.request.env['jabin.user.service'].sudo()
            user_dict = svc.create_user(payload)
            ctx.set_body(ResponseBuilder.created(data=user_dict, message='User created successfully'))
        return ctx.response

    @http.route('/api/v1/users/<int:user_id>', methods=['GET'], type='http', auth='none', csrf=False)
    def get_user(self, user_id: int, **kwargs: Any):
        with self.handle() as ctx:
            svc = http.request.env['jabin.user.service']
            user_dict = svc.get_user(user_id)
            ctx.set_body(ResponseBuilder.success(data=user_dict, message='User retrieved successfully'))
        return ctx.response

    @http.route('/api/v1/users/<int:user_id>', methods=['PUT'], type='http', auth='none', csrf=False)
    def update_user(self, user_id: int, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            svc = http.request.env['jabin.user.service']
            user_dict = svc.update_user(user_id, payload)
            ctx.set_body(ResponseBuilder.success(data=user_dict, message='User updated successfully'))
        return ctx.response

    @http.route('/api/v1/users/<int:user_id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    def delete_user(self, user_id: int, **kwargs: Any):
        with self.handle() as ctx:
            svc = http.request.env['jabin.user.service']
            result = svc.archive_user(user_id)
            ctx.set_body(ResponseBuilder.success(data=result, message='User archived successfully'))
        return ctx.response

    @http.route('/api/v1/users/<int:user_id>/restore', methods=['POST'], type='http', auth='none', csrf=False)
    def restore_user(self, user_id: int, **kwargs: Any):
        with self.handle() as ctx:
            svc = http.request.env['jabin.user.service']
            result = svc.restore_user(user_id)
            ctx.set_body(ResponseBuilder.success(data=result, message='User restored successfully'))
        return ctx.response

    @http.route('/api/v1/users/<int:user_id>/status', methods=['PATCH'], type='http', auth='none', csrf=False)
    def change_status(self, user_id: int, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            status = payload.get('status')
            if not status:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'status', 'message': 'status is required.'}]))
            else:
                svc = http.request.env['jabin.user.service']
                result = svc.set_status(user_id, status)
                ctx.set_body(ResponseBuilder.success(data=result, message='User status updated successfully'))
        return ctx.response
