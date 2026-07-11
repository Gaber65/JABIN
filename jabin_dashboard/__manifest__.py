{
    'name': 'JABIN Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'JABIN Admin Dashboard Framework',
    'description': """
        JABIN Admin Dashboard Foundation Module
        Provides the dashboard framework for JABIN ERP system.
        No business logic included - only dashboard infrastructure.
    """,
    'author': 'JABIN',
    'website': 'https://www.jabin.com',
    'depends': [
        'base',
        'web',
        'jabin_auth'
    ],
    'data': [
        # 'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/dashboard_data.xml',
        'views/dashboard_views.xml',  # Load views BEFORE actions
        'views/actions.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'jabin_dashboard/static/src/css/dashboard.scss',
            'jabin_dashboard/static/src/js/dashboard.js',
            'jabin_dashboard/static/src/xml/dashboard_templates.xml',
        ],
    },
    'demo': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}