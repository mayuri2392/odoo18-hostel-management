# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class OccupancyReport(models.TransientModel):
    _name = 'hostel.occupancy.report'
    _description = 'Occupancy Report Wizard'

    hostel_id = fields.Many2one('hostel.hostel', string='Hostel')
    room_type_id = fields.Many2one('room.type', string='Room Type')
    date_from = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)

    report_type = fields.Selection([
        ('daily', 'Daily Occupancy'),
        ('monthly', 'Monthly Summary'),
        ('detailed', 'Detailed Report')
    ], string='Report Type', default='daily', required=True)

    # ✅ NORMAL (stored) fields - always available to QWeb via docs/object
    total_beds = fields.Integer(string='Total Beds', readonly=True, default=0)
    occupied_beds = fields.Integer(string='Occupied Beds', readonly=True, default=0)
    available_beds = fields.Integer(string='Available Beds', readonly=True, default=0)
    occupancy_rate = fields.Float(string='Occupancy Rate', readonly=True, default=0.0)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for w in self:
            if w.date_from and w.date_to and w.date_from > w.date_to:
                raise UserError(_("From Date cannot be after To Date!"))

    @api.onchange('hostel_id', 'room_type_id', 'date_from', 'date_to')
    def _onchange_refresh_kpis(self):
        for w in self:
            w._refresh_kpis()

    def _refresh_kpis(self):
        """Compute KPIs using your existing model logic (beds + bed.status)."""
        for w in self:
            if not w.date_from or not w.date_to or w.date_from > w.date_to:
                w.total_beds = 0
                w.occupied_beds = 0
                w.available_beds = 0
                w.occupancy_rate = 0.0
                continue

            # Rooms based on filters
            room_domain = [('active', '=', True)]
            if w.hostel_id:
                room_domain.append(('hostel_id', '=', w.hostel_id.id))
            if w.room_type_id:
                room_domain.append(('room_type_id', '=', w.room_type_id.id))
            rooms = self.env['hostel.room'].search(room_domain)

            # Beds from those rooms
            bed_domain = [('active', '=', True)]
            if rooms:
                bed_domain.append(('room_id', 'in', rooms.ids))
            beds = self.env['hostel.bed'].search(bed_domain)

            total_beds = len(beds)
            occupied_beds = len(beds.filtered(lambda b: b.status == 'occupied'))
            available_beds = len(beds.filtered(lambda b: b.status == 'available'))

            rate = (occupied_beds / total_beds) * 100.0 if total_beds else 0.0

            w.total_beds = total_beds
            w.occupied_beds = occupied_beds
            w.available_beds = available_beds
            w.occupancy_rate = round(rate, 2)

    # -----------------------
    # Analysis action (keep your existing or simplified)
    # -----------------------
    def generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("From Date cannot be after To Date!"))

        domain = [('active', '=', True), ('state', 'in', ['active', 'checked_out'])]
        if self.hostel_id:
            domain.append(('hostel_id', '=', self.hostel_id.id))
        if self.room_type_id:
            domain.append(('room_id.room_type_id', '=', self.room_type_id.id))

        if self.report_type == 'monthly':
            hostel_ids = [self.hostel_id.id] if self.hostel_id else self.env['hostel.hostel'].search([('active', '=', True)]).ids
            return {
                'type': 'ir.actions.act_window',
                'name': f'Monthly Occupancy Summary - {self.date_from} to {self.date_to}',
                'res_model': 'hostel.hostel',
                'view_mode': 'list,graph',
                'domain': [('id', 'in', hostel_ids)],
                'context': {'search_default_group_by_type': 1}
            }

        return {
            'type': 'ir.actions.act_window',
            'name': f'Occupancy Report - {self.date_from} to {self.date_to}',
            'res_model': 'hostel.allocation',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_group_by_hostel': 1, 'search_default_group_by_room_type': 1}
        }

    # -----------------------
    # ✅ PDF printing (no payload dependency)
    # -----------------------
    def print_pdf_report(self):
        self.ensure_one()

        # Make sure KPIs are filled on the wizard record
        self._refresh_kpis()

        # This ensures QWeb always has correct values via docs/object
        return self.env.ref('hostel_management.report_occupancy_pdf').report_action(self)
