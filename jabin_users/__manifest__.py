{
    "name": "JABIN Users",
    "version": "17.0.1.0.0",
    "category": "Services/JABIN",
    "summary": "JABIN ERP - User profiles, user types, and multi-address management",
    "description": """
JABIN Users
===========

User-management domain for the JABIN ERP platform.

Provides:
    * Extended res.users with JABIN business fields (user type, balance,
      status, phone, avatar, last login).
    * Multi-address model (jabin.user.address).
    * REST APIs under /api/v1/users and /api/v1/addresses.
    * Service layer keeping business logic out of controllers.

User types: Admin, Customer, Manager, Employee, Driver.
    """,
    "author": "JABIN Engineering",
    "website": "https://github.com/Gaber65/JABIN",
    "license": "Other proprietary",
    "depends": ["base", "jabin_core"],
    "data": [
        # Security (access rights) must load before views/data in Odoo.
        "security/jabin_users_security.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
