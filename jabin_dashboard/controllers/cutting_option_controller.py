from odoo import http
from odoo.http import request
from odoo.addons.jabin_core  import ResponseBuilder
from ..services.cutting_option_service import CuttingOptionService
import json


class CuttingOptionController(http.Controller):

    @http.route('/api/catalog/cutting-option/create', type='json', auth='user', methods=['POST'])
    def create(self, **kwargs):
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs
        vals.pop('id', None)

        option = CuttingOptionService.create(request.env, vals)

        return ResponseBuilder.success(
            data={'id': option.id, 'name': option.name, 'active': option.active},
            message='Cutting Option created successfully'
        )

    @http.route('/api/catalog/cutting-option/<int:option_id>', type='json', auth='user', methods=['GET'])
    def get(self, option_id):
        option = CuttingOptionService.get(request.env, option_id)

        return ResponseBuilder.success(
            data={
                'id': option.id,
                'name': option.name,
                'description': option.description,
                'active': option.active,
                'product_count': len(option.product_ids)
            }
        )

    @http.route('/api/catalog/cutting-options', type='json', auth='user', methods=['GET'])
    def get_all(self, limit=100, offset=0, active=None):
        domain = []
        if active is not None:
            domain.append(('active', '=', active == 'true'))

        options = CuttingOptionService.get_all(
            request.env,
            domain=domain,
            limit=int(limit),
            offset=int(offset)
        )

        return ResponseBuilder.success(
            data={
                'cutting_options': [{
                    'id': o.id,
                    'name': o.name,
                    'description': o.description,
                    'active': o.active,
                } for o in options],
                'total': len(options),
                'limit': int(limit),
                'offset': int(offset)
            }
        )

    @http.route('/api/catalog/cutting-option/<int:option_id>', type='json', auth='user', methods=['PUT'])
    def update(self, option_id, **kwargs):
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs

        option = CuttingOptionService.update(request.env, option_id, vals)

        return ResponseBuilder.success(
            data={'id': option.id, 'name': option.name, 'active': option.active},
            message='Cutting Option updated successfully'
        )

    @http.route('/api/catalog/cutting-option/<int:option_id>', type='json', auth='user', methods=['DELETE'])
    def delete(self, option_id):
        CuttingOptionService.delete(request.env, option_id)

        return ResponseBuilder.success(
            message='Cutting Option deleted successfully'
        )