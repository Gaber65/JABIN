from odoo import fields, models, api
from typing import Dict, Any, Optional


class JabinDashboard(models.Model):
    """Placeholder dashboard model - no business logic"""
    _name = 'jabin.dashboard'
    _description = 'JABIN Dashboard'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Dashboard Name',
        required=True,
        translate=True,
        help='Name of the dashboard section'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display'
    )

    description = fields.Text(
        string='Description',
        translate=True,
        help='Description of the dashboard section'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Toggle to hide/unhide this dashboard section'
    )

    color = fields.Integer(
        string='Color Index',
        default=0,
        help='Color accent for the dashboard section'
    )

    icon = fields.Char(
        string='Icon',
        default='fa-dashboard',
        help='FontAwesome icon class for this dashboard section'
    )

    def _get_kpi_data(self) -> Dict[str, Any]:
        """
        Get placeholder KPI data
        Returns dummy data structure
        """
        return {
            'total_orders': 1234,
            'total_customers': 567,
            'total_products': 89,
            'total_revenue': 123456.78,
            'pending_orders': 45,
            'low_stock': 12,
        }

    def _get_recent_orders(self) -> list:
        """
        Get placeholder recent orders data
        Returns dummy order data
        """
        return [
            {
                'order_number': 'JAB-001',
                'customer': 'Acme Corp',
                'date': '2024-01-15',
                'status': 'Completed',
                'total': 1499.99,
            },
            {
                'order_number': 'JAB-002',
                'customer': 'TechWorld Inc',
                'date': '2024-01-15',
                'status': 'Processing',
                'total': 2499.50,
            },
            {
                'order_number': 'JAB-003',
                'customer': 'Global Solutions',
                'date': '2024-01-14',
                'status': 'Pending',
                'total': 899.00,
            },
        ]

    def _get_top_products(self) -> list:
        """
        Get placeholder top products data
        Returns dummy product data
        """
        return [
            {
                'name': 'Enterprise License',
                'category': 'Software',
                'sales': 24500.00,
                'units': 12,
            },
            {
                'name': 'Premium Support',
                'category': 'Services',
                'sales': 18500.00,
                'units': 24,
            },
            {
                'name': 'Development Kit',
                'category': 'Hardware',
                'sales': 12500.00,
                'units': 18,
            },
        ]

    def _get_chart_data(self) -> Dict[str, Any]:
        """
        Get placeholder chart data
        Returns dummy sales chart data
        """
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'datasets': {
                'sales': [12000, 19000, 15000, 22000, 18000, 25000],
                'orders': [45, 60, 55, 70, 65, 80],
                'customers': [30, 35, 40, 45, 50, 55],
            }
        }


class JabinDashboardSetting(models.TransientModel):
    """Dashboard settings model"""
    _name = 'jabin.dashboard.setting'
    _description = 'JABIN Dashboard Settings'

    dashboard_layout = fields.Selection([
        ('grid', 'Grid'),
        ('compact', 'Compact'),
        ('detailed', 'Detailed'),
    ], string='Dashboard Layout', default='grid', required=True)

    show_kpi = fields.Boolean(string='Show KPI Cards', default=True)
    show_recent_orders = fields.Boolean(string='Show Recent Orders', default=True)
    show_top_products = fields.Boolean(string='Show Top Products', default=True)
    show_sales_chart = fields.Boolean(string='Show Sales Chart', default=True)
    show_inventory_summary = fields.Boolean(string='Show Inventory Summary', default=True)

    refresh_interval = fields.Integer(
        string='Refresh Interval (seconds)',
        default=60,
        help='Time in seconds between auto-refresh of dashboard data'
    )