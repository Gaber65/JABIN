from odoo import http
from odoo.http import request
from jabin_core import ResponseBuilder
from ..services.packaging_service import PackagingService
import json


class PackagingController(http.Controller):

    @http.route('/api/catalog/packaging/create', type='json', auth='user', methods=['POST'])
    def create(self, **kwargs):
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs
        vals.pop('id', None)

        packaging = PackagingService.create(request.env, vals)

        return ResponseBuilder.success(
            data={'id': packaging.id, 'name': packaging.name, 'active': packaging.active},
            message='Packaging created successfully'
        )

    @http.route('/api/catalog/packaging/<int:packaging_id>', type='json', auth='user', methods=['GET'])
    def get(self, packaging_id):
        packaging = PackagingService.get(request.env, packaging_id)

        return ResponseBuilder.success(
            data={
                'id': packaging.id,
                'name': packaging.name,
                'description': packaging.description,
                'active': packaging.active,
                'product_count': len(packaging.product_ids)
            }
        )

    @http.route('/api/catalog/packagings', type='json', auth='user', methods=['GET'])
    def get_all(self, limit=100, offset=0, active=None):
        domain = []
        if active is not None:
            domain.append(('active', '=', active == 'true'))

        packagings = PackagingService.get_all(
            request.env,
            domain=domain,
            limit=int(limit),
            offset=int(offset)
        )

        return ResponseBuilder.success(
            data={
                'packagings': [{
                    'id': p.id,
                    'name': p.name,
                    'description': p.description,
                    'active': p.active,
                } for p in packagings],
                'total': len(packagings),
                'limit': int(limit),
                'offset': int(offset)
            }
        )

    @http.route('/api/catalog/packaging/<int:packaging_id>', type='json', auth='user', methods=['PUT'])
    def update(self, packaging_id, **kwargs):
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs

        packaging = PackagingService.update(request.env, packaging_id, vals)

        return ResponseBuilder.success(
            data={'id': packaging.id, 'name': packaging.name, 'active': packaging.active},
            message='Packaging updated successfully'
        )

    @http.route('/api/catalog/packaging/<int:packaging_id>', type='json', auth='user', methods=['DELETE'])
    def delete(self, packaging_id):
        PackagingService.delete(request.env, packaging_id)

        return ResponseBuilder.success(
            message='Packaging deleted successfully'
        )