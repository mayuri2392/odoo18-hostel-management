# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    hostel_allocation_id = fields.Many2one(
        'hostel.allocation',
        string='Hostel Allocation',
        ondelete='restrict',
        index=True,
        copy=False,
        readonly=True,
    )

    is_hostel_invoice = fields.Boolean(
        string="Hostel Invoice",
        compute='_compute_is_hostel_invoice',
        store=True
    )

    hostel_rent_month = fields.Char(string='Rent Month')

    due_days = fields.Integer(
        string="Days Overdue",
        compute='_compute_due_days',
        store=True
    )

    reminder_sent = fields.Boolean(string="Reminder Sent", default=False)
    last_reminder_date = fields.Date(string="Last Reminder Date")

    # -----------------------------------------------------
    # COMPUTES
    # -----------------------------------------------------
    @api.depends('hostel_allocation_id')
    def _compute_is_hostel_invoice(self):
        for move in self:
            move.is_hostel_invoice = bool(move.hostel_allocation_id)

    @api.depends('invoice_date_due', 'state', 'payment_state', 'is_hostel_invoice')
    def _compute_due_days(self):
        today = fields.Date.today()
        for move in self:
            if (
                move.is_hostel_invoice
                and move.state == 'posted'
                and move.payment_state not in ('paid', 'in_payment')
                and move.invoice_date_due
            ):
                move.due_days = max(0, (today - move.invoice_date_due).days)
            else:
                move.due_days = 0

    # -----------------------------------------------------
    # CREATE OVERRIDE (SAFE + PROFESSIONAL)
    # -----------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Do not break non-hostel invoices
        for vals in vals_list:
            allocation_id = vals.get('hostel_allocation_id')
            if allocation_id:
                allocation = self.env['hostel.allocation'].browse(allocation_id).exists()
                if allocation:
                    vals.setdefault('invoice_origin', f'Hostel Allocation: {allocation.name}')
                    if not vals.get('partner_id') and allocation.tenant_id and allocation.tenant_id.partner_id:
                        vals['partner_id'] = allocation.tenant_id.partner_id.id

        return super().create(vals_list)

    # -----------------------------------------------------
    # INTERNAL SYNC HELPERS
    # -----------------------------------------------------
    def _hostel_sync_allocation_and_tenant(self):
        moves = self.filtered(lambda m: m.is_hostel_invoice and m.hostel_allocation_id)
        if not moves:
            return

        allocations = moves.mapped('hostel_allocation_id')
        tenants = allocations.mapped('tenant_id')

        # Your existing working sync methods
        allocations._compute_payment_info()
        allocations._compute_deposit_summary()

        # Tenant sync (stored fields)
        if tenants:
            tenants._compute_payment_totals()
            tenants._compute_invoice_count()

    # -----------------------------------------------------
    # POST / WRITE HOOKS
    # -----------------------------------------------------
    def action_post(self):
        res = super().action_post()

        hostel_moves = self.filtered(lambda m: m.is_hostel_invoice and m.hostel_allocation_id)
        hostel_moves._hostel_sync_allocation_and_tenant()

        for move in hostel_moves:
            # Post message on allocation chatter
            move.hostel_allocation_id.message_post(
                body=_("Invoice <b>%s</b> posted (Amount: %s)") % (move.name, move.amount_total)
            )
        return res

    def write(self, vals):
        res = super().write(vals)

        # Sync only when relevant accounting fields changed
        if {'state', 'payment_state', 'amount_residual'} & set(vals):
            moves = self.filtered(lambda m: m.is_hostel_invoice and m.hostel_allocation_id)
            if moves:
                moves._hostel_sync_allocation_and_tenant()

                # Reset reminder flags on full payment
                for move in moves:
                    if move.payment_state in ('paid', 'in_payment') or float(move.amount_residual or 0.0) == 0.0:
                        move.reminder_sent = False
                        move.last_reminder_date = False

        return res

    # -----------------------------------------------------
    # REMINDER ACTION
    # -----------------------------------------------------
    def action_send_payment_reminder(self):
        self.ensure_one()

        if not self.is_hostel_invoice:
            raise UserError(_("This is not a hostel invoice."))

        if self.state != 'posted' or self.payment_state in ('paid', 'in_payment'):
            raise UserError(_("Reminder can be sent only for unpaid posted invoices."))

        template = self.env.ref('hostel_management.email_template_payment_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)

        self.write({'reminder_sent': True, 'last_reminder_date': fields.Date.today()})
        self.message_post(body=_("Payment reminder sent to tenant."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminder Sent'),
                'message': _('Payment reminder sent successfully.'),
                'type': 'success'
            }
        }

    # -----------------------------------------------------
    # DELETE RULES
    # -----------------------------------------------------
    def unlink(self):
        for move in self:
            if move.is_hostel_invoice and move.state == 'posted':
                raise UserError(_("You cannot delete a posted hostel invoice."))
        return super().unlink()

    # -----------------------------------------------------
    # DISPLAY NAME
    # -----------------------------------------------------
    def name_get(self):
        res = []
        for move in self:
            name = move.name
            if move.is_hostel_invoice and move.hostel_allocation_id:
                tenant = move.hostel_allocation_id.tenant_id
                if tenant:
                    name = f"{name} - {tenant.name}"
            res.append((move.id, name))
        return res
