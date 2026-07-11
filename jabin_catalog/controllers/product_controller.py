from odoo import http
from odoo.http import request
from jabin_core import ResponseBuilder
from ..services.product_service import ProductService
import json


class ProductController(http.Controller):

    @http.route('/api/catalog/product/create', type='json', auth='user', methods=['POST'])
    def create_product(self, **kwargs):
        """Create a new product"""
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs
        vals.pop('id', None)

        product = ProductService.create_product(request.env, vals)

        return ResponseBuilder.success(
            data={
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'selling_price': product.selling_price,
                'offer_price': product.offer_price,
                'is_on_offer': product.is_on_offer,
                'stock_quantity': product.stock_quantity,
            },
            message='Product created successfully'
        )

    @http.route('/api/catalog/product/<int:product_id>', type='json', auth='user', methods=['GET'])
    def get_product(self, product_id):
        """Get a single product"""
        product = ProductService.get_product(request.env, product_id)

        return ResponseBuilder.success(
            data={
                'id': product.id,
                'category_id': product.category_id.id,
                'category_name': product.category_id.name,
                'name': product.name,
                'description': product.description,
                'sku': product.sku,
                'barcode': product.barcode,
                'purchase_price': product.purchase_price,
                'selling_price': product.selling_price,
                'discount_type': product.discount_type,
                'discount_value': product.discount_value,
                'offer_price': product.offer_price,
                'offer_start_date': product.offer_start_date,
                'offer_end_date': product.offer_end_date,
                'is_on_offer': product.is_on_offer,
                'profit': product.profit,
                'offer_profit': product.offer_profit,
                'profit_percentage': product.profit_percentage,
                'stock_quantity': product.stock_quantity,
                'minimum_stock': product.minimum_stock,
                'weight': product.weight,
                'preparation_time': product.preparation_time,
                'main_image': product.main_image and product.main_image.decode('utf-8') if product.main_image else None,
                'active': product.active,
                'is_available': product.is_available,
                'is_featured': product.is_featured,
                'is_best_seller': product.is_best_seller,
                'cutting_options': [{
                    'id': opt.id,
                    'name': opt.name,
                } for opt in product.cutting_option_ids],
                'packaging_options': [{
                    'id': pkg.id,
                    'name': pkg.name,
                } for pkg in product.packaging_ids],
                'excluded_parts': [{
                    'id': part.id,
                    'name': part.name,
                } for part in product.excluded_part_ids],
                'images': [{
                    'id': img.id,
                    'sequence': img.sequence,
                    'image': img.image and img.image.decode('utf-8') if img.image else None,
                } for img in product.product_image_ids],
            }
        )

    @http.route('/api/catalog/products', type='json', auth='user', methods=['GET'])
    def get_products(self, limit=100, offset=0, category_id=None, active=None, on_offer=None):
        """Get list of products with filters"""
        domain = []

        if category_id:
            domain.append(('category_id', '=', int(category_id)))

        if active is not None:
            domain.append(('active', '=', active == 'true'))

        if on_offer is not None:
            domain.append(('is_on_offer', '=', on_offer == 'true'))

        products = ProductService.get_products(
            request.env,
            domain=domain,
            limit=int(limit),
            offset=int(offset)
        )

        return ResponseBuilder.success(
            data={
                'products': [{
                    'id': p.id,
                    'name': p.name,
                    'sku': p.sku,
                    'category_name': p.category_id.name,
                    'selling_price': p.selling_price,
                    'offer_price': p.offer_price,
                    'is_on_offer': p.is_on_offer,
                    'stock_quantity': p.stock_quantity,
                    'is_available': p.is_available,
                    'is_featured': p.is_featured,
                    'is_best_seller': p.is_best_seller,
                } for p in products],
                'total': len(products),
                'limit': int(limit),
                'offset': int(offset)
            }
        )

    @http.route('/api/catalog/product/<int:product_id>', type='json', auth='user', methods=['PUT'])
    def update_product(self, product_id, **kwargs):
        """Update a product"""
        vals = json.loads(request.httprequest.data) if request.httprequest.data else kwargs

        product = ProductService.update_product(request.env, product_id, vals)

        return ResponseBuilder.success(
            data={
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
            },
            message='Product updated successfully'
        )

    @http.route('/api/catalog/product/<int:product_id>', type='json', auth='user', methods=['DELETE'])
    def delete_product(self, product_id):
        """Delete a product"""
        ProductService.delete_product(request.env, product_id)

        return ResponseBuilder.success(
            message='Product deleted successfully'
        )

    @http.route('/api/catalog/product/<int:product_id>/stock', type='json', auth='user', methods=['POST'])
    def update_stock(self, product_id):
        """Update product stock"""
        data = json.loads(request.httprequest.data)
        quantity = data.get('quantity', 0)

        product = ProductService.update_stock(request.env, product_id, quantity)

        return ResponseBuilder.success(
            data={
                'id': product.id,
                'name': product.name,
                'stock_quantity': product.stock_quantity,
                'is_available': product.is_available,
            },
            message=f'Stock updated by {quantity} units'
        )