# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class HostelPortal(CustomerPortal):

    def _get_tenant_for_current_user(self):
        partner = request.env.user.partner_id
        Tenant = request.env['hostel.tenant']

        # tenant record linked to current portal user's partner
        tenant = Tenant.search([('partner_id', '=', partner.id)], limit=1)
        return tenant

    @http.route(['/my/hostel'], type='http', auth='user', website=True)
    def portal_my_hostel(self, **kw):
        tenant = self._get_tenant_for_current_user()
        if not tenant:
            # if user is portal but not linked to a tenant, show empty page
            return request.render('hostel_management.portal_my_hostel', {
                'tenant': False,
                'current_allocation': False,
                'allocations': [],
            })

        Allocation = request.env['hostel.allocation']

        # Always filter by tenant_id to avoid leaks even if record rules are loose
        allocations = Allocation.search(
            [('tenant_id', '=', tenant.id)],
            order='check_in_date desc'
        )

        current_allocation = allocations.filtered(lambda a: a.state == 'active')[:1] or allocations[:1]

        return request.render('hostel_management.portal_my_hostel', {
            'tenant': tenant,
            'current_allocation': current_allocation and current_allocation[0] or False,
            'allocations': allocations,
        })
