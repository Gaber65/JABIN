/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useState } from '@odoo/owl';

class JabinDashboardComponent extends Component {
    setup() {
        super.setup();

        this.state = useState({
            loading: false,
            kpiData: {
                total_orders: 1234,
                total_customers: 567,
                total_products: 89,
                total_revenue: 123456.78,
                pending_orders: 45,
                low_stock: 12,
            },
            recentOrders: [
                {
                    order_number: 'JAB-001',
                    customer: 'Acme Corp',
                    date: '2024-01-15',
                    status: 'Completed',
                    total: 1499.99,
                },
                {
                    order_number: 'JAB-002',
                    customer: 'TechWorld Inc',
                    date: '2024-01-15',
                    status: 'Processing',
                    total: 2499.50,
                },
                {
                    order_number: 'JAB-003',
                    customer: 'Global Solutions',
                    date: '2024-01-14',
                    status: 'Pending',
                    total: 899.00,
                },
            ],
            topProducts: [
                {
                    name: 'Enterprise License',
                    category: 'Software',
                    sales: 24500.00,
                    units: 12,
                },
                {
                    name: 'Premium Support',
                    category: 'Services',
                    sales: 18500.00,
                    units: 24,
                },
                {
                    name: 'Development Kit',
                    category: 'Hardware',
                    sales: 12500.00,
                    units: 18,
                },
            ],
            salesData: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: {
                    sales: [12000, 19000, 15000, 22000, 18000, 25000],
                    orders: [45, 60, 55, 70, 65, 80],
                    customers: [30, 35, 40, 45, 50, 55],
                }
            },
            inventoryData: {
                total: 1500,
                low_stock: 45,
                out_of_stock: 12,
                categories: 15,
            },
            error: null,
        });
    }

    get formattedRevenue() {
        const revenue = this.state.kpiData.total_revenue || 0;
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(revenue);
    }

    get formattedOrders() {
        return (this.state.kpiData.total_orders || 0).toLocaleString();
    }

    get formattedCustomers() {
        return (this.state.kpiData.total_customers || 0).toLocaleString();
    }

    get formattedProducts() {
        return (this.state.kpiData.total_products || 0).toLocaleString();
    }

    get formattedPendingOrders() {
        return (this.state.kpiData.pending_orders || 0).toLocaleString();
    }

    get formattedLowStock() {
        return (this.state.kpiData.low_stock || 0).toLocaleString();
    }
}

JabinDashboardComponent.template = 'jabin_dashboard.DashboardComponent';

// Register the dashboard client action
registry.category('actions').add('jabin_dashboard.dashboard_view', JabinDashboardComponent);