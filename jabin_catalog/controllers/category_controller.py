from jabin_core import ResponseBuilder
from odoo import http
from odoo.http import request
from ..services.category_service import CategoryService
import json


class CategoryController(http.Controller):

    @http.route('/api/catalog/category/create', type='json', auth='user', methods=['POST'])
    def create_category(self, **kwargs):
        """Create a new category"""
        try:
            vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs
            vals.pop('id', None)

            category = CategoryService.create_category(request.env, vals)

            return ResponseBuilder.success(
                data={
                    'id': category.id,
                    'name': category.name,
                    'sequence': category.sequence,
                    'active': category.active,
                    'product_count': category.product_count,
                },
                message='Category created successfully'
            )
        except Exception as e:
            # Global Exception Handler will catch this
            raise

    @http.route('/api/catalog/category/<int:category_id>', type='json', auth='user', methods=['GET'])
    def get_category(self, category_id):
        """Get a single category"""
        category = CategoryService.get_category(request.env, category_id)

        return ResponseBuilder.success(
            data={
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'image': category.image and category.image.decode('utf-8') if category.image else None,
                'sequence': category.sequence,
                'active': category.active,
                'product_count': category.product_count,
                'products': [{
                    'id': p.id,
                    'name': p.name,
                    'sku': p.sku,
                    'selling_price': p.selling_price,
                    'is_on_offer': p.is_on_offer,
                } for p in category.product_ids[:10]]
            }
        )

    @http.route('/api/catalog/categories', type='json', auth='user', methods=['GET'])
    def get_categories(self, limit=100, offset=0, active=None):
        """Get list of categories"""
        domain = []
        if active is not None:
            domain.append(('active', '=', active == 'true'))

        categories = CategoryService.get_categories(
            request.env,
            domain=domain,
            limit=int(limit),
            offset=int(offset)
        )

        return ResponseBuilder.success(
            data={
                'categories': [{
                    'id': c.id,
                    'name': c.name,
                    'description': c.description,
                    'sequence': c.sequence,
                    'active': c.active,
                    'product_count': c.product_count,
                } for c in categories],
                'total': len(categories),
                'limit': int(limit),
                'offset': int(offset)
            }
        )

    @http.route('/api/catalog/category/<int:category_id>', type='json', auth='user', methods=['PUT'])
    def update_category(self, category_id, **kwargs):
        """Update a category"""
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs

        category = CategoryService.update_category(request.env, category_id, vals)

        return ResponseBuilder.success(
            data={
                'id': category.id,
                'name': category.name,
                'sequence': category.sequence,
                'active': category.active,
            },
            message='Category updated successfully'
        )

    @http.route('/api/catalog/category/<int:category_id>', type='json', auth='user', methods=['DELETE'])
    def delete_category(self, category_id):
        """Delete a category"""
        CategoryService.delete_category(request.env, category_id)

        return ResponseBuilder.success(
            message='Category deleted successfully'
        )
