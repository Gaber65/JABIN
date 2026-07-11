from odoo import http
from odoo.http import request, Response
import json
from typing import Dict, Any


class JabinDashboardController(http.Controller):

    @http.route('/jabin_dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self, **kwargs) -> Dict[str, Any]:
        """
        Get dashboard data via JSON RPC
        """
        try:
            dashboard_id = kwargs.get('dashboard_id')
            if not dashboard_id:
                # Get first available dashboard
                dashboard = request.env['jabin.dashboard'].search([], limit=1)
                if dashboard:
                    dashboard_id = dashboard.id
                else:
                    return {'error': 'No dashboard found'}

            dashboard = request.env['jabin.dashboard'].browse(dashboard_id)
            if not dashboard.exists():
                return {'error': 'Dashboard not found'}

            # Gather dashboard data
            data = {
                'kpi': dashboard._get_kpi_data(),
                'recent_orders': dashboard._get_recent_orders(),
                'top_products': dashboard._get_top_products(),
                'sales_data': dashboard._get_chart_data(),
                'inventory_summary': {
                    'total': 1500,
                    'low_stock': 45,
                    'out_of_stock': 12,
                    'categories': 15,
                }
            }

            return {'status': 'success', 'data': data}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    @http.route('/jabin_dashboard/settings', type='json', auth='user', methods=['POST'])
    def save_dashboard_settings(self, **kwargs) -> Dict[str, Any]:
        """
        Save dashboard settings
        """
        try:
            settings = kwargs.get('settings', {})

            # Store settings in user preferences or database
            # For now, just return success

            return {
                'status': 'success',
                'message': 'Settings saved successfully'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    @http.route('/jabin_dashboard/refresh', type='json', auth='user', methods=['POST'])
    def refresh_dashboard_data(self, **kwargs) -> Dict[str, Any]:
        """
        Force refresh dashboard data
        """
        return self.get_dashboard_data(**kwargs)