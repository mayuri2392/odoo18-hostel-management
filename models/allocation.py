# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import formatLang
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class HostelAllocation(models.Model):
    _name = 'hostel.allocation'
    _description = 'Hostel Room Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_in_date desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    active = fields.Boolean(default=True)

    state = fields.Selection(
        [('draft', 'Draft'),
         ('active', 'Active'),
         ('checked_out', 'Checked Out'),
         ('cancelled', 'Cancelled')],
        default='draft',
        tracking=True
    )

    tenant_id = fields.Many2one('hostel.tenant', required=True, domain="[('active','=',True)]")
    hostel_id = fields.Many2one('hostel.hostel', required=True)
    room_id = fields.Many2one('hostel.room', required=True)
    bed_id = fields.Many2one('hostel.bed', required=True)

    filtered_room_ids = fields.Many2many('hostel.room', compute='_compute_filtered_rooms')
    filtered_bed_ids = fields.Many2many('hostel.bed', compute='_compute_filtered_beds')

    preferred_room_type_id = fields.Many2one('room.type')
    preferred_ac_type = fields.Selection([('ac', 'AC'), ('non_ac', 'Non-AC')])

    check_in_date = fields.Date(required=True, default=fields.Date.today)
    expected_check_out_date = fields.Date()
    actual_check_out_date = fields.Date(tracking=True)

    duration_days = fields.Integer(compute='_compute_duration', store=False)

    monthly_rent = fields.Float(
        compute='_compute_monthly_rent',
        store=True,
        readonly=False,
        required=True,
        tracking=True
    )

    # =====================================================
    # ✅ FIX: AVAILABLE SERVICES DOMAIN (JS-SAFE)
    # =====================================================
    hostel_service_ids = fields.Many2many(
        'hostel.service.type',
        compute='_compute_hostel_services',
        store=False,
    )

    # Per-person services
    service_ids = fields.Many2many(
        'hostel.service.type',
        string='Services',
        domain="[('id','in',hostel_service_ids)]",
        help="Per-person services billed along with rent.",
    )

    service_monthly_charge = fields.Monetary(
        string="Services Charge",
        currency_field="currency_id",
        compute="_compute_service_charges",
        store=True
    )

    total_monthly_charge = fields.Monetary(
        string="Total Monthly Charge",
        currency_field="currency_id",
        compute="_compute_service_charges",
        store=True
    )

    security_deposit = fields.Float(string="Security Deposit", required=True)

    invoice_ids = fields.One2many('account.move', 'hostel_allocation_id')
    invoice_count = fields.Integer(compute='_compute_invoice_count', store=True)

    paid_amount = fields.Float(compute='_compute_payment_info', store=True)
    due_amount = fields.Float(compute='_compute_payment_info', store=True)

    total_invoiced_amount = fields.Monetary(
        string="Total Invoiced",
        currency_field="currency_id",
        compute="_compute_invoice_summary",
        store=False,
    )
    outstanding_amount = fields.Monetary(
        string="Outstanding",
        currency_field="currency_id",
        compute="_compute_invoice_summary",
        store=False,
    )

    payment_status = fields.Selection(
        [('unpaid', 'Unpaid'), ('partial', 'Partial'), ('paid', 'Paid')],
        compute='_compute_payment_info',
        store=True
    )

    rent_payment_day = fields.Integer(default=1)
    next_payment_date = fields.Date(compute='_compute_next_payment_date')
    notes = fields.Text()

    deposit_move_id = fields.Many2one('account.move', string="Security Deposit Invoice", readonly=True, tracking=True)
    deposit_refund_move_id = fields.Many2one('account.move', string="Security Deposit Refund (Credit Note)", readonly=True, tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, store=True)

    deposit_in_amount = fields.Monetary(string="Deposit Received", currency_field='currency_id',
                                        compute="_compute_deposit_summary", store=True)
    deposit_out_amount = fields.Monetary(string="Deposit Refunded", currency_field='currency_id',
                                         compute="_compute_deposit_summary", store=True)
    deposit_balance = fields.Monetary(string="Deposit Balance", currency_field='currency_id',
                                      compute="_compute_deposit_summary", store=True)

    deposit_status = fields.Selection([
        ('none', 'Not Created'),
        ('invoiced', 'Invoiced'),
        ('received', 'Received'),
        ('refund_created', 'Refund Created'),
        ('refunded', 'Refunded'),
    ], compute="_compute_deposit_summary", store=True)

    deposit_ledger_count = fields.Integer(compute="_compute_deposit_ledger_count")

    can_checkout = fields.Boolean(compute="_compute_can_checkout", store=False)
    checkout_block_reason = fields.Char(compute="_compute_can_checkout", store=False)

    _sql_constraints = [
        ('bed_unique_active', "UNIQUE(bed_id) WHERE state = 'active'", 'This bed is already allocated!')
    ]

    # =====================================================
    # ✅ helper compute: allowed services from hostel
    # =====================================================
    @api.depends('hostel_id')
    def _compute_hostel_services(self):
        for rec in self:
            rec.hostel_service_ids = rec.hostel_id.service_ids if rec.hostel_id else False

    # Optional but recommended: if hostel changes, drop invalid selected services
    @api.onchange('hostel_id')
    def _onchange_hostel_id_services_cleanup(self):
        if not self.hostel_id:
            self.service_ids = [(5, 0, 0)]
            return
        allowed = self.hostel_id.service_ids
        self.service_ids = self.service_ids.filtered(lambda s: s in allowed)

    # =====================================================
    # CREATE
    # =====================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hostel.allocation') or 'ALL/NEW'
        return super().create(vals_list)

    # =====================================================
    # FILTERED ROOMS / BEDS
    # =====================================================
    @api.depends('hostel_id', 'preferred_room_type_id', 'preferred_ac_type')
    def _compute_filtered_rooms(self):
        for rec in self:
            if not rec.hostel_id:
                rec.filtered_room_ids = False
                continue
            domain = [
                ('hostel_id', '=', rec.hostel_id.id),
                ('active', '=', True),
                ('status', '=', 'available'),
            ]
            if rec.preferred_room_type_id:
                domain.append(('room_type_id', '=', rec.preferred_room_type_id.id))
            rec.filtered_room_ids = self.env['hostel.room'].search(domain)

    @api.depends('room_id')
    def _compute_filtered_beds(self):
        for rec in self:
            if rec.room_id:
                rec.filtered_bed_ids = self.env['hostel.bed'].search([
                    ('room_id', '=', rec.room_id.id),
                    ('active', '=', True),
                    ('status', '=', 'available'),
                ])
            else:
                rec.filtered_bed_ids = False

    # =====================================================
    # RENT / DURATION
    # =====================================================
    @api.depends('bed_id', 'room_id')
    def _compute_monthly_rent(self):
        for rec in self:
            if rec.bed_id:
                rec.monthly_rent = rec.bed_id.rent_amount
            elif rec.room_id:
                rec.monthly_rent = rec.room_id.rent_amount
            else:
                rec.monthly_rent = 0.0

    @api.depends('hostel_id', 'service_ids', 'monthly_rent')
    def _compute_service_charges(self):
        """Compute service charges and total monthly charge (safe)."""
        for rec in self:
            service_total = 0.0
            if rec.hostel_id and rec.service_ids:
                get_rate = getattr(rec.hostel_id, '_get_service_rent', None)
                for srv in rec.service_ids:
                    rate = get_rate(srv) if get_rate else 0.0
                    service_total += float(rate or 0.0)

            rec.service_monthly_charge = service_total
            rec.total_monthly_charge = float(rec.monthly_rent or 0.0) + service_total

    @api.onchange('room_id')
    def _onchange_room_id(self):
        self.bed_id = False

    @api.depends('check_in_date', 'actual_check_out_date', 'state')
    def _compute_duration(self):
        for rec in self:
            days = 0
            if rec.check_in_date and rec.state == 'active':
                days = (fields.Date.today() - rec.check_in_date).days
            elif rec.check_in_date and rec.actual_check_out_date:
                days = (rec.actual_check_out_date - rec.check_in_date).days
            rec.duration_days = max(days, 0)

    # =====================================================
    # PAYMENT INFO
    # =====================================================
    @api.depends('invoice_ids.state', 'invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.move_type')
    def _compute_payment_info(self):
        for rec in self:
            invoices = rec.invoice_ids.filtered(lambda i: i.state == 'posted' and i.move_type == 'out_invoice')
            total = sum(invoices.mapped('amount_total'))
            residual = sum(invoices.mapped('amount_residual'))
            rec.paid_amount = total - residual
            rec.due_amount = residual

            if total == 0:
                rec.payment_status = 'unpaid'
            elif residual == 0:
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'partial'

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund')))

    @api.depends('invoice_ids.state', 'invoice_ids.move_type', 'invoice_ids.amount_total', 'invoice_ids.amount_residual')
    def _compute_invoice_summary(self):
        for rec in self:
            invoices = rec.invoice_ids.filtered(lambda i: i.state == 'posted' and i.move_type == 'out_invoice')
            total = sum(invoices.mapped('amount_total'))
            residual = sum(invoices.mapped('amount_residual'))
            rec.total_invoiced_amount = total
            rec.outstanding_amount = residual

    # =====================================================
    # CAN CHECKOUT (kept only for future/reporting; not used to disable buttons)
    # =====================================================
    @api.depends('state', 'due_amount')
    def _compute_can_checkout(self):
        for rec in self:
            if rec.state != 'active':
                rec.can_checkout = False
                rec.checkout_block_reason = _("Checkout is allowed only in Active state.")
                continue
            if (rec.due_amount or 0.0) > 0.0:
                rec.can_checkout = False
                rec.checkout_block_reason = _("Pending due amount exists. Please register payment before checkout.")
            else:
                rec.can_checkout = True
                rec.checkout_block_reason = False

    # =====================================================
    # NEXT PAYMENT DATE
    # =====================================================
    @api.depends('check_in_date', 'rent_payment_day')
    def _compute_next_payment_date(self):
        for rec in self:
            if not rec.check_in_date:
                rec.next_payment_date = False
                continue
            base = rec.check_in_date
            today = fields.Date.today()
            while base <= today:
                base += timedelta(days=30)
            rec.next_payment_date = base

    # =====================================================
    # CRON
    # =====================================================
    @api.model
    def _cron_generate_monthly_invoices(self):
        today = fields.Date.today().replace(day=1)
        allocations = self.search([('state', '=', 'active')])
        for alloc in allocations:
            existing = alloc.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice'
                and inv.invoice_date
                and inv.invoice_date.replace(day=1) == today
            )
            if not existing:
                alloc._create_monthly_rent_invoice()

    # =====================================================
    # ACTIONS
    # =====================================================
    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            conflict = self.search([
                ('bed_id', '=', rec.bed_id.id),
                ('state', '=', 'active'),
                ('id', '!=', rec.id),
            ], limit=1)
            if conflict:
                raise ValidationError(_("This bed is already allocated to another active tenant."))
            rec.state = 'active'
            rec._create_first_rent_invoice()
            rec._create_security_deposit_invoice()

    def action_checkout(self):
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(_("Only active allocations can be checked out."))

            # ✅ Professional: popup warning on click (no ugly banner)
            if (rec.due_amount or 0.0) > 0.0:
                due_str = formatLang(self.env, rec.due_amount, currency_obj=rec.currency_id)
                raise UserError(_(
                    "Cannot Check Out\n\n"
                    "This allocation has unpaid invoices.\n"
                    "Due Amount: %(due)s\n\n"
                    "Open the invoices and register payment, then try again."
                ) % {'due': due_str})

            # ✅ Legacy safeguard: create deposit invoice if missing
            if rec.security_deposit > 0 and not rec.deposit_move_id:
                rec._create_security_deposit_invoice()

            # Create refund credit note if needed
            if rec.deposit_move_id and not rec.deposit_refund_move_id:
                rec._create_security_deposit_refund_credit_note()

            if not rec.actual_check_out_date:
                rec.actual_check_out_date = fields.Date.today()

            rec.state = 'checked_out'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'checked_out':
                raise ValidationError(_("Checked-out allocations cannot be cancelled."))
            rec.state = 'cancelled'

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('hostel_allocation_id', '=', self.id), ('move_type', 'in', ('out_invoice', 'out_refund'))],
            'context': {'create': False},
        }

    def action_open_unpaid_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Unpaid Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('hostel_allocation_id', '=', self.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0),
            ],
            'context': {'create': False},
        }

    def action_view_tenant(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'hostel.tenant', 'view_mode': 'form', 'res_id': self.tenant_id.id}

    def action_view_hostel(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'hostel.hostel', 'view_mode': 'form', 'res_id': self.hostel_id.id}

    def action_view_room(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'hostel.room', 'view_mode': 'form', 'res_id': self.room_id.id}

    def action_view_bed(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'hostel.bed', 'view_mode': 'form', 'res_id': self.bed_id.id}

    # =====================================================
    # LEGACY FIX ACTIONS (for old records you cannot delete)
    # =====================================================
    def action_generate_deposit_documents(self):
        self.ensure_one()
        if self.security_deposit <= 0:
            raise UserError(_("No Security Deposit amount found."))

        if not self.deposit_move_id:
            self._create_security_deposit_invoice()

        if self.state == 'checked_out' and self.deposit_move_id and not self.deposit_refund_move_id:
            self._create_security_deposit_refund_credit_note()

        return self.action_open_deposit_panel()

    def action_fix_legacy_deposits_bulk(self):
        repaired = 0
        skipped = 0
        for rec in self:
            try:
                if rec.security_deposit > 0 and not rec.deposit_move_id:
                    rec._create_security_deposit_invoice()
                    repaired += 1

                if rec.state == 'checked_out' and rec.deposit_move_id and not rec.deposit_refund_move_id:
                    rec._create_security_deposit_refund_credit_note()
                    repaired += 1
            except Exception:
                _logger.exception("Failed to repair deposit docs for allocation %s", rec.name)
                skipped += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Legacy Deposit Repair"),
                'message': _("Repaired: %s | Skipped: %s") % (repaired, skipped),
                'sticky': False,
            }
        }

    # =====================================================
    # ACCOUNTS
    # =====================================================
    def _get_income_account(self):
        account = self.env['account.account'].search([('account_type', '=', 'income'), ('deprecated', '=', False)], limit=1)
        if not account:
            raise UserError(_("No Income account found.\nPlease create an Income account in Accounting → Configuration → Chart of Accounts."))
        return account

    def _get_deposit_account(self):
        account = self.env['account.account'].search([('internal_group', '=', 'liability'), ('deprecated', '=', False)], limit=1)
        if not account:
            raise UserError(_("No Liability account found for Security Deposit.\nPlease create a Security Deposit Liability account."))
        return account

    # =====================================================
    # INVOICE CREATION
    # =====================================================
    def _create_first_rent_invoice(self):
        self.ensure_one()
        invoice = self._create_monthly_rent_invoice()
        invoice.ref = f"First Rent - {self.name}"
        return invoice

    def _create_monthly_rent_invoice(self):
        self.ensure_one()
        if not self.tenant_id.partner_id:
            raise UserError(_("Tenant must have a linked Contact."))

        income_account = self._get_income_account()
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            '|', ('company_id', '=', self.env.company.id),
                 ('company_id', '=', False),
        ], limit=1)

        invoice_lines = [(0, 0, {
            'name': f'Hostel Rent - {self.bed_id.name}',
            'quantity': 1,
            'price_unit': self.monthly_rent,
            'account_id': income_account.id,
            'tax_ids': [(6, 0, tax.ids)] if tax else [],
        })]

        # Add per-person services (if selected)
        if self.service_ids:
            missing_rate = []
            for srv in self.service_ids:
                rate = self.hostel_id._get_service_rent(srv) if self.hostel_id else 0.0
                if rate <= 0:
                    missing_rate.append(srv.name)
                    continue
                invoice_lines.append((0, 0, {
                    'name': f'Service - {srv.name}',
                    'quantity': 1,
                    'price_unit': rate,
                    'account_id': income_account.id,
                    'tax_ids': [(6, 0, tax.ids)] if tax else [],
                }))

            if missing_rate:
                raise UserError(_(
                    "Service rates are not configured for: %(services)s\n\n"
                    "Go to Hostel → Rent Configuration → Service Rates and set monthly charges."
                ) % {'services': ', '.join(missing_rate)})

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.partner_id.id,
            'hostel_allocation_id': self.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        })
        return invoice

    def _create_security_deposit_invoice(self):
        self.ensure_one()
        if self.security_deposit <= 0 or self.deposit_move_id:
            return
        if not self.tenant_id.partner_id:
            raise UserError(_("Tenant must have a linked Contact."))

        deposit_account = self._get_deposit_account()
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.partner_id.id,
            'hostel_allocation_id': self.id,
            'invoice_date': fields.Date.today(),
            'ref': f"Security Deposit - {self.name}",
            'invoice_line_ids': [(0, 0, {
                'name': f"Security Deposit - {self.name}",
                'quantity': 1,
                'price_unit': self.security_deposit,
                'account_id': deposit_account.id,
                'tax_ids': [(6, 0, [])],
            })],
        })
        inv.action_post()
        self.deposit_move_id = inv.id

    def _create_security_deposit_refund_credit_note(self):
        self.ensure_one()
        if not self.deposit_move_id or self.deposit_refund_move_id:
            return
        if self.security_deposit <= 0:
            return

        deposit_account = self._get_deposit_account()
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.tenant_id.partner_id.id,
            'hostel_allocation_id': self.id,
            'invoice_date': fields.Date.today(),
            'ref': f"Deposit Refund - {self.name}",
            'invoice_line_ids': [(0, 0, {
                'name': f"Deposit Refund - {self.name}",
                'quantity': 1,
                'price_unit': self.security_deposit,
                'account_id': deposit_account.id,
                'tax_ids': [(6, 0, [])],
            })],
        })
        refund.action_post()
        self.deposit_refund_move_id = refund.id

    # =====================================================
    # DEPOSIT SUMMARY
    # =====================================================
    def _compute_deposit_ledger_count(self):
        for rec in self:
            rec.deposit_ledger_count = int(bool(rec.deposit_move_id)) + int(bool(rec.deposit_refund_move_id))

    @api.depends(
        'security_deposit',
        'deposit_move_id.state', 'deposit_move_id.payment_state', 'deposit_move_id.amount_total', 'deposit_move_id.amount_residual',
        'deposit_refund_move_id.state', 'deposit_refund_move_id.payment_state', 'deposit_refund_move_id.amount_total', 'deposit_refund_move_id.amount_residual',
    )
    def _compute_deposit_summary(self):
        """
        IMPORTANT FIX:
        In Odoo 18, after Register Payment, invoices can be 'in_payment' even though residual is 0.
        Treat (payment_state in ('paid','in_payment') OR residual == 0) as received/refunded.
        """
        for rec in self:
            deposit_in = 0.0
            deposit_out = 0.0

            dep = rec.deposit_move_id
            ref = rec.deposit_refund_move_id

            dep_received = bool(dep and dep.state == 'posted' and (
                dep.payment_state in ('paid', 'in_payment') or float(dep.amount_residual or 0.0) == 0.0
            ))
            ref_paid = bool(ref and ref.state == 'posted' and (
                ref.payment_state in ('paid', 'in_payment') or float(ref.amount_residual or 0.0) == 0.0
            ))

            if dep_received:
                deposit_in = dep.amount_total
            if ref_paid:
                deposit_out = ref.amount_total

            rec.deposit_in_amount = deposit_in
            rec.deposit_out_amount = deposit_out
            rec.deposit_balance = deposit_in - deposit_out

            if not dep:
                rec.deposit_status = 'none'
            elif dep and not dep_received and not ref:
                rec.deposit_status = 'invoiced'
            elif dep_received and not ref:
                rec.deposit_status = 'received'
            elif ref and not ref_paid:
                rec.deposit_status = 'refund_created'
            elif ref_paid:
                rec.deposit_status = 'refunded'
            else:
                rec.deposit_status = 'invoiced'

    # =====================================================
    # DEPOSIT ACTIONS
    # =====================================================
    def action_view_deposit_ledger(self):
        self.ensure_one()
        move_ids = []
        if self.deposit_move_id:
            move_ids.append(self.deposit_move_id.id)
        if self.deposit_refund_move_id:
            move_ids.append(self.deposit_refund_move_id.id)
        if not move_ids:
            raise UserError(_("Security Deposit documents were not created yet."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Security Deposit'),
            'res_model': 'account.move',
            'views': [(self.env.ref('hostel_management.view_account_move_deposit_ledger_list').id, 'list'), (False, 'form')],
            'domain': [('id', 'in', move_ids)],
            'context': {'create': False, 'edit': False},
        }

    def action_view_deposit_lines(self):
        self.ensure_one()
        move_ids = []
        if self.deposit_move_id:
            move_ids.append(self.deposit_move_id.id)
        if self.deposit_refund_move_id:
            move_ids.append(self.deposit_refund_move_id.id)
        if not move_ids:
            raise UserError(_("No deposit ledger lines found."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Security Deposit Ledger Lines'),
            'res_model': 'account.move.line',
            'views': [(self.env.ref('hostel_management.view_deposit_ledger_move_line_list').id, 'list'), (False, 'form')],
            'domain': [('move_id', 'in', move_ids)],
            'context': {'create': False, 'edit': False},
        }

    def action_open_deposit_panel(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Security Deposit'),
            'res_model': 'hostel.allocation',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('hostel_management.view_allocation_deposit_panel_form').id, 'form')],
            'target': 'new',
            'context': dict(self.env.context),
        }
