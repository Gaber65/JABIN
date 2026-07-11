from odoo import http
from odoo.http import request
from odoo.addons.jabin_core  import ResponseBuilder
from ..services.excluded_part_service import ExcludedPartService
import json


class ExcludedPartController(http.Controller):

    @http.route('/api/catalog/excluded-part/create', type='json', auth='user', methods=['POST'])
    def create(self, **kwargs):
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs
        vals.pop('id', None)

        part = ExcludedPartService.create(request.env, vals)

        return ResponseBuilder.success(
            data={'id': part.id, 'name': part.name, 'active': part.active},
            message='Excluded Part created successfully'
        )

    @http.route('/api/catalog/excluded-part/<int:part_id>', type='json', auth='user', methods=['GET'])
    def get(self, part_id):
        part = ExcludedPartService.get(request.env, part_id)

        return ResponseBuilder.success(
            data={
                'id': part.id,
                'name': part.name,
                'description': part.description,
                'active': part.active,
                'product_count': len(part.product_ids)
            }
        )

    @http.route('/api/catalog/excluded-parts', type='json', auth='user', methods=['GET'])
    def get_all(self, limit=100, offset=0, active=None):
        domain = []
        if active is not None:
            domain.append(('active', '=', active == 'true'))

        parts = ExcludedPartService.get_all(
            request.env,
            domain=domain,
            limit=int(limit),
            offset=int(offset)
        )

        return ResponseBuilder.success(
            data={
                'excluded_parts': [{
                    'id': p.id,
                    'name': p.name,
                    'description': p.description,
                    'active': p.active,
                } for p in parts],
                'total': len(parts),
                'limit': int(limit),
                'offset': int(offset)
            }
        )

    @http.route('/api/catalog/excluded-part/<int:part_id>', type='json', auth='user', methods=['PUT'])
    def update(self, part_id, **kwargs):
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs

        part = ExcludedPartService.update(request.env, part_id, vals)

        return ResponseBuilder.success(
            data={'id': part.id, 'name': part.name, 'active': part.active},
            message='Excluded Part updated successfully'
        )

    @http.route('/api/catalog/excluded-part/<int:part_id>', type='json', auth='user', methods=['DELETE'])
    def delete(self, part_id):
        ExcludedPartService.delete(request.env, part_id)

        return ResponseBuilder.success(
            message='Excluded Part deleted successfully'
        )