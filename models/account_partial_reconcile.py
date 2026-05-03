# -*- coding: utf-8 -*-
from odoo import models, api


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._hostel_sync_allocations_and_tenants()
        return recs

    def unlink(self):
        allocations = self._hostel_get_allocations()
        tenants = allocations.mapped('tenant_id') if allocations else self.env['hostel.tenant']

        res = super().unlink()

        if allocations:
            allocations._compute_payment_info()
            allocations._compute_deposit_summary()

        if tenants:
            tenants._compute_payment_totals()
            tenants._compute_invoice_count()

        return res

    # -----------------------------------------------------
    # HELPERS
    # -----------------------------------------------------
    def _hostel_get_allocations(self):
        allocations = self.env['hostel.allocation']
        for r in self:
            lines = (r.debit_move_id + r.credit_move_id)
            moves = lines.move_id.filtered(
                lambda m: getattr(m, 'is_hostel_invoice', False) and m.hostel_allocation_id
            )
            allocations |= moves.mapped('hostel_allocation_id')
        return allocations

    def _hostel_sync_allocations_and_tenants(self):
        allocations = self._hostel_get_allocations()
        if allocations:
            allocations._compute_payment_info()
            allocations._compute_deposit_summary()

            tenants = allocations.mapped('tenant_id')
            if tenants:
                tenants._compute_payment_totals()
                tenants._compute_invoice_count()
