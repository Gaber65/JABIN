{
    'name': 'JABIN Catalog Module',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom Catalog Management System',
    'description': """
        Complete custom catalog module for JABIN.
        Includes categories, products with pricing, offers, and media management.
        Reuses infrastructure from jabin_core.
    """,
    'author': 'JABIN',
    'website': 'https://jabin.com',
    'depends': [
        'base',
        'web',
        'mail',
        'jabin_core',
        'jabin_api',
        'jabin_security',
        'jabin_auth',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/category_views.xml',
        'views/product_views.xml',
        'views/cutting_option_views.xml',
        'views/packaging_views.xml',
        'views/excluded_part_views.xml',
        'views/menu_views.xml',
        'data/demo_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}