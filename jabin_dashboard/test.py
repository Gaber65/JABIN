from pathlib import Path

PROJECT_NAME = "jabin_dashboard"

FILES = [
    "__manifest__.py",
    "__init__.py",

    "security/ir.model.access.csv",

    "views/templates.xml",
    "views/assets.xml",

    "static/src/app.js",

    "static/src/components/layout/layout.js",
    "static/src/components/layout/layout.xml",
    "static/src/components/layout/layout.scss",

    "static/src/components/sidebar/sidebar.js",
    "static/src/components/sidebar/sidebar.xml",
    "static/src/components/sidebar/sidebar.scss",
    "static/src/components/sidebar/sidebar_item.js",
    "static/src/components/sidebar/sidebar_item.xml",
    "static/src/components/sidebar/sidebar_group.js",

    "static/src/components/header/header.js",
    "static/src/components/header/header.xml",
    "static/src/components/header/header.scss",
    "static/src/components/header/user_dropdown.js",
    "static/src/components/header/notification_bell.js",

    "static/src/components/ui/card/.gitkeep",
    "static/src/components/ui/stat_card/.gitkeep",
    "static/src/components/ui/breadcrumb/.gitkeep",
    "static/src/components/ui/empty_state/.gitkeep",
    "static/src/components/ui/loading_skeleton/.gitkeep",
    "static/src/components/ui/chart_placeholder/.gitkeep",
    "static/src/components/ui/table_placeholder/.gitkeep",

    "static/src/components/pages/dashboard_page.js",
    "static/src/components/pages/catalog_page.js",
    "static/src/components/pages/orders_page.js",
    "static/src/components/pages/customers_page.js",
    "static/src/components/pages/marketing_page.js",
    "static/src/components/pages/reports_page.js",
    "static/src/components/pages/settings_page.js",

    "static/src/services/navigation_registry.js",
    "static/src/services/routing_service.js",
    "static/src/services/theme_service.js",

    "static/src/hooks/use_navigation.js",
    "static/src/hooks/use_routing.js",
    "static/src/hooks/use_theme.js",

    "static/src/utils/constants.js",
    "static/src/utils/helpers.js",

    "static/src/styles/main.scss",
    "static/src/styles/variables.scss",
    "static/src/styles/mixins.scss",
    "static/src/styles/global.scss",

    "data/navigation_data.xml",

    "README.md",
]

ROOT = Path(PROJECT_NAME)

for file in FILES:
    path = ROOT / file
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.touch()

print("=" * 50)
print(f"Project '{PROJECT_NAME}' created successfully!")
print(f"Location: {ROOT.resolve()}")
print("=" * 50)