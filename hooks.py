# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Only admins should see portal grant/revoke actions
    admin_group = env.ref('base.group_system')

    # Action menu items are usually ir.actions.server bound to res.partner
    actions = env['ir.actions.server'].search([
        ('binding_model_id.model', '=', 'res.partner'),
        ('name', 'in', ['Grant portal access', 'Revoke portal access']),
    ])

    # Some databases use slightly different names; be tolerant
    if not actions:
        actions = env['ir.actions.server'].search([
            ('binding_model_id.model', '=', 'res.partner'),
            ('name', 'ilike', 'portal'),
        ])

    for act in actions:
        act.groups_id = [(6, 0, [admin_group.id])]
