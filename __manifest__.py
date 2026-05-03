{
    'name': 'Hostel Management',
    'version': '18.0.1.0.0',
    'summary': 'Manage Hostels and Paying Guest Accommodations',
    'category': 'Property Management',
    'author': 'Mayuri Patil',

    'depends': ['web', 'mail', 'account', 'utm', 'portal', 'contacts'],
    'post_init_hook': 'post_init_hook',

    'data': [
        'security/ir.model.access.csv',
        'security/hostel_portal_rules.xml',
        'data/sequence.xml',
        'data/cron.xml',

        # Core views
        'views/room_type_views.xml',
        'views/facility_type_views.xml',
        'views/service_type_views.xml',
        'views/hostel_views.xml',
        'views/room_views.xml',
        'views/bed_views.xml',
        'views/tenant_views.xml',
        'views/allocation_views.xml',
        'views/account_inherited_views.xml',
        'views/occupancy_report_views.xml',
        'views/hostel_gallery_views.xml',
        'views/portal_templates.xml',


        # Reports
        'report/hostel_invoice_template.xml',
        'report/report_action.xml',
        'report/occupancy_report.xml',

        # Menus LAST
        'views/menus.xml',
    ],

    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
