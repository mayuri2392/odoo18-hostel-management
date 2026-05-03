# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import email_normalize
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class HostelTenant(models.Model):
    _name = 'hostel.tenant'
    _description = 'Hostel Tenant'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('uniq_partner_id', 'unique(partner_id)', 'A tenant already exists for this customer.'),
    ]

    # =====================================================
    # PARTNER LINK
    # =====================================================
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        domain=[('company_type', '=', 'person')],
        tracking=True
    )

    name = fields.Char(related='partner_id.name', store=True, readonly=False, required=True, tracking=True)
    email = fields.Char(related='partner_id.email', readonly=False, tracking=True)
    mobile = fields.Char(related='partner_id.mobile', readonly=False, tracking=True)
    image_1920 = fields.Image(related='partner_id.image_1920', readonly=False)

    user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        readonly=True,
        copy=False,
        ondelete='set null',
        tracking=True
    )

    portal_state = fields.Selection(
        [('no', 'No Access'), ('invited', 'Invited'), ('active', 'Active')],
        string="Portal Status",
        compute="_compute_portal_state",
        store=False
    )

    # =====================================================
    # ADDRESS
    # =====================================================
    street = fields.Char(related='partner_id.street', readonly=False)
    street2 = fields.Char(related='partner_id.street2', readonly=False)
    city = fields.Char(related='partner_id.city', readonly=False)
    state_id = fields.Many2one(related='partner_id.state_id', readonly=False)
    country_id = fields.Many2one(related='partner_id.country_id', readonly=False)
    zip = fields.Char(related='partner_id.zip', readonly=False)
    full_address = fields.Text(compute='_compute_full_address', store=True)

    # =====================================================
    # TENANT IDENTIFICATION
    # =====================================================
    tenant_code = fields.Char(string='Tenant ID', readonly=True, copy=False, tracking=True)

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], tracking=True)

    date_of_birth = fields.Date(tracking=True)
    age = fields.Integer(compute='_compute_age', store=True)

    id_proof_type = fields.Selection([
        ('aadhar', 'Aadhar Card'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('college_id', 'College ID'),
        ('voter_id', 'Voter ID'),
        ('other', 'Other')
    ], tracking=True)

    id_proof_number = fields.Char(tracking=True)

    # =====================================================
    # EMERGENCY CONTACT
    # =====================================================
    emergency_contact = fields.Char(tracking=True)
    emergency_phone = fields.Char(tracking=True)
    emergency_relation = fields.Selection([
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('spouse', 'Spouse'),
        ('friend', 'Friend'),
        ('other', 'Other')
    ], tracking=True)

    # =====================================================
    # ACADEMIC
    # =====================================================
    college_name = fields.Char(tracking=True)
    course = fields.Char(tracking=True)
    year_of_study = fields.Selection([
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
        ('5', '5th Year'),
        ('postgrad', 'Post Graduate')
    ], tracking=True)

    # =====================================================
    # ALLOCATIONS
    # =====================================================
    allocation_ids = fields.One2many('hostel.allocation', 'tenant_id')

    has_open_allocation = fields.Boolean(compute='_compute_has_open_allocation', store=True)
    has_active_allocation = fields.Boolean(compute='_compute_has_active_allocation', store=True)
    current_allocation_id = fields.Many2one('hostel.allocation', compute='_compute_current_allocation')
    allocation_count = fields.Integer(compute='_compute_allocation_count')
    draft_allocation_id = fields.Many2one('hostel.allocation', compute='_compute_draft_allocation')

    # =====================================================
    # PAYMENTS
    # =====================================================
    total_amount_paid = fields.Float(compute='_compute_payment_totals', store=True)
    total_amount_due = fields.Float(compute='_compute_payment_totals', store=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count', store=True)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # =====================================================
    # STATUS
    # =====================================================
    active = fields.Boolean(default=True, tracking=True)
    registration_date = fields.Date(default=fields.Date.today, readonly=True)
    last_allocation_date = fields.Date(compute='_compute_last_allocation_date')

    # =====================================================
    # CREATE (SEQUENCE)
    # =====================================================
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence'].sudo()
        for vals in vals_list:
            if not vals.get('tenant_code'):
                code = seq.next_by_code('hostel.tenant')
                if not code:
                    raise UserError(
                        "Tenant ID sequence is missing.\n"
                        "Please check Settings → Technical → Sequences."
                    )
                vals['tenant_code'] = code
        return super().create(vals_list)

    # =====================================================
    # COMPUTES
    # =====================================================
    @api.depends('street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _compute_full_address(self):
        for tenant in self:
            tenant.full_address = ', '.join(filter(None, [
                tenant.street,
                tenant.street2,
                tenant.city,
                tenant.state_id.name if tenant.state_id else None,
                tenant.zip,
                tenant.country_id.name if tenant.country_id else None,
            ]))

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for tenant in self:
            if tenant.date_of_birth:
                tenant.age = today.year - tenant.date_of_birth.year - (
                    (today.month, today.day) <
                    (tenant.date_of_birth.month, tenant.date_of_birth.day)
                )
            else:
                tenant.age = 0

    @api.depends('allocation_ids.state', 'allocation_ids.check_in_date', 'allocation_ids.create_date')
    def _compute_draft_allocation(self):
        for tenant in self:
            draft_alloc = tenant.allocation_ids.filtered(lambda a: a.state == 'draft').sorted('create_date', reverse=True)
            tenant.draft_allocation_id = draft_alloc[:1].id if draft_alloc else False

    @api.depends('allocation_ids.state')
    def _compute_has_open_allocation(self):
        for tenant in self:
            tenant.has_open_allocation = any(a.state in ('draft', 'active') for a in tenant.allocation_ids)

    @api.depends('allocation_ids.state')
    def _compute_has_active_allocation(self):
        for tenant in self:
            tenant.has_active_allocation = any(a.state == 'active' for a in tenant.allocation_ids)

    @api.depends('allocation_ids.state')
    def _compute_current_allocation(self):
        for tenant in self:
            active_alloc = tenant.allocation_ids.filtered(lambda a: a.state == 'active').sorted('check_in_date', reverse=True)
            tenant.current_allocation_id = active_alloc[:1].id if active_alloc else False

    @api.depends('allocation_ids.state')
    def _compute_allocation_count(self):
        for tenant in self:
            tenant.allocation_count = len(tenant.allocation_ids.filtered(lambda a: a.state != 'draft'))

    @api.depends('allocation_ids.invoice_count', 'allocation_ids.state')
    def _compute_invoice_count(self):
        for tenant in self:
            allocations = tenant.allocation_ids.filtered(lambda a: a.state in ('active', 'checked_out'))
            tenant.invoice_count = sum(allocations.mapped('invoice_count'))

    @api.depends('allocation_ids.state', 'allocation_ids.paid_amount', 'allocation_ids.due_amount')
    def _compute_payment_totals(self):
        for tenant in self:
            allocations = tenant.allocation_ids.filtered(lambda a: a.state in ('active', 'checked_out'))
            tenant.total_amount_paid = sum(allocations.mapped('paid_amount'))
            tenant.total_amount_due = sum(allocations.mapped('due_amount'))

    def _compute_last_allocation_date(self):
        for tenant in self:
            tenant.last_allocation_date = max(tenant.allocation_ids.mapped('check_in_date'), default=False)

    # =====================================================
    # PORTAL STATUS
    # =====================================================
    def _compute_portal_state(self):
        for tenant in self:
            if not tenant.user_id:
                tenant.portal_state = 'no'
            else:
                tenant.portal_state = 'active' if tenant.user_id.login_date else 'invited'

    # =====================================================
    # PORTAL ACTIONS (ENTERPRISE SAFE)
    # =====================================================
    def action_invite_to_portal(self):
        """Invite tenant to portal.
        - requires unique email on partner
        - prevents duplicate contacts using same email
        - reuses existing user if login exists
        - makes user portal (and removes internal group if needed)
        """
        self.ensure_one()

        partner = self.partner_id
        if not partner:
            raise UserError(_("Tenant must have a linked Customer first."))

        if not partner.email:
            raise UserError(_("Customer email is required to grant portal access."))

        email = partner.email.strip()
        email_norm = email_normalize(email)
        if not email_norm:
            raise UserError(_("Please set a valid email address on the Customer."))

        Partner = self.env['res.partner'].sudo()
        dup_partner = Partner.search([
            ('email_normalized', '=', email_norm),
            ('id', '!=', partner.id),
        ], limit=1)
        if dup_partner:
            raise UserError(_(
                "This email is already used by another contact:\n"
                "%s\n\n"
                "Portal access requires a unique email per contact.\n"
                "Please merge contacts or use a unique email."
            ) % dup_partner.display_name)

        portal_group = self.env.ref('base.group_portal')
        internal_group = self.env.ref('base.group_user')
        Users = self.env['res.users'].sudo()

        # Reuse existing user (by partner or login)
        user = partner.user_ids[:1] or Users.search([('login', '=', email)], limit=1)

        if user:
            # Ensure user linked to our partner
            if user.partner_id.id != partner.id:
                user.write({'partner_id': partner.id})

            vals = {'groups_id': [(4, portal_group.id)]}
            if internal_group in user.groups_id:
                vals['groups_id'].append((3, internal_group.id))
            user.write(vals)
        else:
            user = Users.create({
                'name': partner.name,
                'login': email,
                'email': email,
                'partner_id': partner.id,
                'groups_id': [(6, 0, [portal_group.id])],
            })

        # Send invite email
        user.action_reset_password()

        # Link to tenant
        self.user_id = user.id
        return True

    def action_resend_portal_invite(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("No portal user linked. Please invite first."))
        self.user_id.sudo().action_reset_password()
        return True

    def action_revoke_portal_access(self):
        self.ensure_one()
        if not self.user_id:
            return True
        portal_group = self.env.ref('base.group_portal')
        self.user_id.sudo().write({'groups_id': [(3, portal_group.id)]})
        self.sudo().write({'user_id': False})
        return True

    # =====================================================
    # OTHER ACTIONS
    # =====================================================
    def action_create_allocation(self):
        self.ensure_one()
        existing = self.env['hostel.allocation'].search([
            ('tenant_id', '=', self.id),
            ('state', 'in', ('draft', 'active')),
        ], limit=1)
        if existing:
            raise UserError(
                "This tenant already has an open allocation (Draft or Active). "
                "Please complete or cancel it first."
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Allocation',
            'res_model': 'hostel.allocation',
            'view_mode': 'form',
            'context': {'default_tenant_id': self.id},
        }

    def action_resume_draft_allocation(self):
        self.ensure_one()
        draft = self.env['hostel.allocation'].search([
            ('tenant_id', '=', self.id),
            ('state', '=', 'draft'),
        ], order='create_date desc', limit=1)

        if not draft:
            raise UserError("No draft allocation found for this tenant.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Resume Allocation',
            'res_model': 'hostel.allocation',
            'view_mode': 'form',
            'res_id': draft.id,
            'target': 'current',
            'context': {'default_tenant_id': self.id},
        }

    def action_view_allocations(self):
        self.ensure_one()
        allocations = self.env['hostel.allocation'].search([('tenant_id', '=', self.id)])

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Allocations',
            'res_model': 'hostel.allocation',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }
        if len(allocations) == 1:
            action.update({'view_mode': 'form', 'res_id': allocations.id, 'domain': []})
        return action

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('hostel_allocation_id.tenant_id', '=', self.id),
                ('move_type', '=', 'out_invoice')
            ],
            'context': {'default_partner_id': self.partner_id.id},
        }

    def action_view_partner(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
        }

    # =====================================================
    # DISPLAY
    # =====================================================
    def name_get(self):
        return [(t.id, f"[{t.tenant_code}] {t.name}") for t in self]
