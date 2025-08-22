{
    'name': 'Barkir Core',
    'version': '18.0.1.0.0',
    'summary': 'Core models for Customs and Container Management',
    'description': """
This module contains the core data models for managing containers, shipments, 
and packaging (kemasan), including chatter and activity tracking.
    """,
    'category': 'Customs',
    'author': 'DPS',
    'website': '-',
    'depends': ['base', 'mail'],
    'data': [
        'security/dps_container_security.xml',
        'security/ir.model.access.csv',
        'views/dps_container.xml',
        'views/dps_kemasan.xml',
        'views/dps_shipment.xml',
        'views/dps_pjt.xml',
        'views/dps_reference.xml',
        'views/menu.xml',
        # 'views/dps_shipment_views.xml', # Added new view file
        # 'views/dps_container_menus.xml',
        # 'views/dps_kemasan_menus.xml',
        # 'views/dps_shipment_menus.xml', # Added new menu file
    ],
    'icon': '/barkir_core/static/img/icon.png',
    'application': True,
    'installable': True,
    'auto_install': False,
}
