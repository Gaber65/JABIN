from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import ensure_db


class DashboardController(http.Controller):

    @http.route('/jabin_dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self, **kwargs):
        """Get all dashboard data"""
        ensure_db()

        # Get the dashboard service
        service = request.env['jabin.dashboard.service'].sudo()

        # Get all dashboard data
        data = service.get_dashboard_data()

        return {
            'status': 'success',
            'data': data
        }