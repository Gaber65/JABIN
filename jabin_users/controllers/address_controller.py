from __future__ import annotations
from typing import Any

from odoo import http
from odoo.addons.jabin_core import ResponseBuilder, ValidationHelper
from odoo.addons.jabin_api.controllers.base import BaseApiController


class AddressController(BaseApiController):

    @http.route('/api/v1/addresses', methods=['GET'], type='http', auth='none', csrf=False)
    def list_addresses(self, **kwargs: Any):
        with self.handle() as ctx:
            user_id = ValidationHelper.to_int(kwargs.get('user_id'), None)
            if not user_id:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'user_id', 'message': 'user_id is required.'}]))
            else:
                page = ValidationHelper.to_int(kwargs.get('page'), 1) or 1
                per_page = ValidationHelper.to_int(kwargs.get('per_page'), 20) or 20
                svc = http.request.env['jabin.address.service']
                (data, meta) = svc.list_addresses(user_id=user_id, page=page, per_page=per_page)
                ctx.set_body(ResponseBuilder.success(data=data, meta=meta, message='Addresses retrieved successfully'))
        return ctx.response

    @http.route('/api/v1/addresses', methods=['POST'], type='http', auth='none', csrf=False)
    def create_address(self, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            user_id = ValidationHelper.to_int(payload.get('user_id'), None)
            if not user_id:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'user_id', 'message': 'user_id is required.'}]))
            else:
                svc = http.request.env['jabin.address.service']
                addr_dict = svc.create_address(user_id, payload)
                ctx.set_body(ResponseBuilder.created(data=addr_dict, message='Address created successfully'))
        return ctx.response

    @http.route('/api/v1/addresses/<int:address_id>', methods=['GET'], type='http', auth='none', csrf=False)
    def get_address(self, address_id: int, **kwargs: Any):
        with self.handle() as ctx:
            user_id = ValidationHelper.to_int(kwargs.get('user_id'), None)
            if not user_id:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'user_id', 'message': 'user_id is required.'}]))
            else:
                svc = http.request.env['jabin.address.service']
                addr_dict = svc.get_address(address_id, user_id)
                ctx.set_body(ResponseBuilder.success(data=addr_dict, message='Address retrieved successfully'))
        return ctx.response

    @http.route('/api/v1/addresses/<int:address_id>', methods=['PUT'], type='http', auth='none', csrf=False)
    def update_address(self, address_id: int, **kwargs: Any):
        with self.handle() as ctx:
            payload = self.parse_json_body()
            user_id = ValidationHelper.to_int(payload.pop('user_id', None), None)
            if not user_id:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'user_id', 'message': 'user_id is required.'}]))
            else:
                svc = http.request.env['jabin.address.service']
                addr_dict = svc.update_address(address_id, user_id, payload)
                ctx.set_body(ResponseBuilder.success(data=addr_dict, message='Address updated successfully'))
        return ctx.response

    @http.route('/api/v1/addresses/<int:address_id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    def delete_address(self, address_id: int, **kwargs: Any):
        with self.handle() as ctx:
            user_id = ValidationHelper.to_int(kwargs.get('user_id'), None)
            if not user_id:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'user_id', 'message': 'user_id is required.'}]))
            else:
                svc = http.request.env['jabin.address.service']
                result = svc.delete_address(address_id, user_id)
                ctx.set_body(ResponseBuilder.success(data=result, message='Address deleted successfully'))
        return ctx.response

    @http.route('/api/v1/addresses/<int:address_id>/default', methods=['POST'], type='http', auth='none', csrf=False)
    def set_default_address(self, address_id: int, **kwargs: Any):
        with self.handle() as ctx:
            user_id = ValidationHelper.to_int(kwargs.get('user_id'), None)
            if not user_id:
                ctx.set_body(
                    ResponseBuilder.validation_error([{'field': 'user_id', 'message': 'user_id is required.'}]))
            else:
                svc = http.request.env['jabin.address.service']
                result = svc.set_default(address_id, user_id)
                ctx.set_body(ResponseBuilder.success(data=result, message='Default address set successfully'))
        return ctx.response
