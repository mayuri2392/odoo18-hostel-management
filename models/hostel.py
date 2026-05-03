# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

# =====================================================
# ROOM CATEGORY
# =====================================================
class RoomType(models.Model):
    _name = 'room.type'
    _description = 'Room Type'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    default_capacity = fields.Integer(
        string='Default Capacity',
        required=True,
        default=1
    )
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Room type name must be unique!'),
    ]


# =====================================================
# FACILITY CATALOG
# =====================================================
class FacilityType(models.Model):
    _name = 'facility.type'
    _description = 'Facility Type'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Facility type name must be unique!'),
    ]


# =====================================================
# ROOM RATE CONFIGURATION (HOSTEL-WISE)
# =====================================================
class HostelRentConfig(models.Model):
    _name = 'hostel.rent.config'
    _description = 'Hostel Room Rate Configuration'

    hostel_id = fields.Many2one(
        'hostel.hostel',
        string='Hostel',
        required=True
    )

    room_type_id = fields.Many2one(
        'room.type',
        string='Room Type',
        required=True
    )

    base_rent = fields.Float(
        string='Rent per Person',
        required=True,
        default=0.0
    )

    _sql_constraints = [
        (
            'hostel_room_type_uniq',
            'unique(hostel_id, room_type_id)',
            'Room rate for this room category already exists for this hostel!'
        ),
    ]


# =====================================================
# ADD-ON RATE CONFIGURATION (HOSTEL-WISE)
# =====================================================
class HostelFacilityRentConfig(models.Model):
    _name = 'hostel.facility.rent.config'
    _description = 'Hostel Add-on Rate Configuration'

    hostel_id = fields.Many2one(
        'hostel.hostel',
        string='Hostel',
        required=True
    )

    facility_type_id = fields.Many2one(
        'facility.type',
        string='Add-on',
        required=True
    )

    additional_rent = fields.Float(
        string='Additional Monthly Charge',
        required=True,
        default=0.0
    )

    _sql_constraints = [
        (
            'hostel_facility_uniq',
            'unique(hostel_id, facility_type_id)',
            'Rate for this add-on already exists for this hostel!'
        ),
    ]

    # -------------------------------------------------
    # SAFETY CHECK: ONLY SELECTED ADD-ONS CAN BE PRICED
    # -------------------------------------------------
    @api.constrains('facility_type_id', 'hostel_id')
    def _check_facility_is_selected_addon(self):
        for rec in self:
            if rec.hostel_id and rec.facility_type_id:
                if rec.facility_type_id not in rec.hostel_id.extra_facility_ids:
                    raise ValidationError(_(
                        "You can configure rates only for facilities selected "
                        "in Hostel → Add-ons."
                    ))


# =====================================================
# ✅ SERVICE CATALOG (PER PERSON)
# =====================================================
class HostelServiceType(models.Model):
    _name = 'hostel.service.type'
    _description = 'Hostel Service'
    _order = 'name'

    name = fields.Char(string='Service Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Service name must be unique!'),
    ]


# =====================================================
# ✅ SERVICE RATE CONFIGURATION (HOSTEL-WISE)
# =====================================================
class HostelServiceRentConfig(models.Model):
    _name = 'hostel.service.rent.config'
    _description = 'Hostel Service Rate Configuration'

    hostel_id = fields.Many2one(
        'hostel.hostel',
        string='Hostel',
        required=True,
        ondelete='cascade'
    )

    service_type_id = fields.Many2one(
        'hostel.service.type',
        string='Service',
        required=True,
        ondelete='restrict'
    )

    monthly_charge = fields.Float(
        string='Monthly Charge (Per Person)',
        required=True,
        default=0.0
    )

    _sql_constraints = [
        (
            'hostel_service_uniq',
            'unique(hostel_id, service_type_id)',
            'Rate for this service already exists for this hostel!'
        ),
    ]

    # -------------------------------------------------
    # SAFETY CHECK: ONLY SELECTED SERVICES CAN BE PRICED
    # -------------------------------------------------
    @api.constrains('service_type_id', 'hostel_id')
    def _check_service_is_selected(self):
        for rec in self:
            if rec.hostel_id and rec.service_type_id:
                if rec.service_type_id not in rec.hostel_id.service_ids:
                    raise ValidationError(_(
                        "You can configure rates only for services selected "
                        "in Hostel → Services."
                    ))


class HostelImage(models.Model):
    _name = 'hostel.image'
    _description = 'Hostel Image'

    image = fields.Image(
        string='Image',
        required=True,
        max_width=1920,
        max_height=1920
    )
    hostel_id = fields.Many2one(
        'hostel.hostel',
        required=True,
        ondelete='cascade'
    )


class HostelHostel(models.Model):
    _name = 'hostel.hostel'
    _description = 'Hostel/PG Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Hostel/PG Name', required=True, tracking=True)
    type = fields.Selection([
        ('hostel', 'Hostel'),
        ('pg', 'Paying Guest (PG)')
    ], string='Type', required=True, default='hostel', tracking=True)
    address = fields.Text(string='Address', required=True)

    # Image fields
    image_1920 = fields.Image(string='Main Image', max_width=1920, max_height=1920)
    image_1024 = fields.Image(string="Image 1024", related="image_1920", max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image(string="Image 512", related="image_1920", max_width=512, max_height=512, store=True)
    image_128 = fields.Image(string="Image 128", related="image_1920", max_width=128, max_height=128, store=True)

    image_ids = fields.One2many(
        'hostel.image',
        'hostel_id',
        string='Gallery'
    )

    # Boolean fields for facilities - ALL POSSIBLE FIELDS
    facility_bed = fields.Boolean(string="Bed", default=True)
    facility_table = fields.Boolean(string="Table", default=True)
    facility_chair = fields.Boolean(string="Chair", default=True)
    facility_cupboard = fields.Boolean(string="Cupboard", default=True)
    facility_fan = fields.Boolean(string="Fan", default=True)
    facility_lights = fields.Boolean(string="Lights", default=True)
    facility_common_bathroom = fields.Boolean(string="Common Bathroom", default=True)
    facility_attached_bathroom = fields.Boolean(string="Attached Bathroom", default=False)
    facility_cleaning = fields.Boolean(string="Cleaning Services", default=True)
    facility_wifi = fields.Boolean(string="Wi-Fi", default=True)
    facility_balcony = fields.Boolean(string="Balcony", default=False)
    facility_ac = fields.Boolean(string="Air Conditioner", default=False)

    # Extra facilities (user-defined)
    extra_facility_ids = fields.Many2many(
        'facility.type',
        string='Add-ons',
        help="Add-ons available at additional monthly charges."
    )

    # ✅ Services (Per Person)
    service_ids = fields.Many2many(
        'hostel.service.type',
        string='Services',
        help="Per-person services available in this hostel (Gym/Mess/Parking etc.)."
    )

    contact_person = fields.Char(string='Contact Person')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')

    # Relations
    room_ids = fields.One2many('hostel.room', 'hostel_id', string='Rooms')
    allocation_ids = fields.One2many('hostel.allocation', 'hostel_id', string='Allocations')

    # Rent configurations
    rent_config_ids = fields.One2many('hostel.rent.config', 'hostel_id', string='Room Rent Configuration')
    facility_rent_config_ids = fields.One2many(
        'hostel.facility.rent.config',
        'hostel_id',
        string='Facility Rent Configuration'
    )

    # ✅ Service rate configuration (Per Person)
    service_rate_config_ids = fields.One2many(
        'hostel.service.rent.config',
        'hostel_id',
        string='Service Rate Configuration'
    )

    # Computed fields
    total_rooms = fields.Integer(string='Total Rooms', compute='_compute_stats', store=True)
    total_beds = fields.Integer(string='Total Beds', compute='_compute_stats', store=True)
    available_beds = fields.Integer(string='Available Beds', compute='_compute_stats', store=True)
    occupied_beds = fields.Integer(string='Occupied Beds', compute='_compute_stats', store=True)
    occupancy_rate = fields.Float(string='Occupancy Rate', compute='_compute_stats', store=True)
    allocation_count = fields.Integer(string='Allocations', compute='_compute_allocation_count')
    room_count = fields.Integer(string='Room Count', compute='_compute_room_count')

    # Floor information (computed)
    floor_info = fields.Char(string='Floors', compute='_compute_floor_info')
    min_floor = fields.Integer(string='Lowest Floor', compute='_compute_floor_stats')
    max_floor = fields.Integer(string='Highest Floor', compute='_compute_floor_stats')

    gallery_image_count = fields.Integer(
        string="Gallery Images",
        compute="_compute_gallery_image_count",
        store=False
    )

    # Active field
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Hostel/PG name must be unique!'),
    ]

    def _get_room_type_rent(self, room_type_id):
        """Get rent for a room type in this hostel"""
        self.ensure_one()
        config = self.rent_config_ids.filtered(lambda r: r.room_type_id.id == room_type_id.id)
        return config.base_rent if config else 0.0

    def _get_facility_rent(self, facility_type_id):
        """Get additional rent for a facility in this hostel"""
        self.ensure_one()
        config = self.facility_rent_config_ids.filtered(lambda f: f.facility_type_id.id == facility_type_id.id)
        return config.additional_rent if config else 0.0

    def _get_service_rent(self, service_type_id):
        """Return monthly charge for a service based on hostel configuration."""
        self.ensure_one()
        if not service_type_id:
            return 0.0
        line = self.service_rate_config_ids.filtered(
            lambda l: l.service_type_id.id == service_type_id.id
        )[:1]
        return line.monthly_charge if line else 0.0

    def _compute_gallery_image_count(self):
        for hostel in self:
            hostel.gallery_image_count = len(hostel.image_ids)

    @api.depends('room_ids', 'room_ids.bed_ids', 'room_ids.bed_ids.status')
    def _compute_stats(self):
        for hostel in self:
            rooms = hostel.room_ids.filtered(lambda r: r.active)
            total_rooms = len(rooms)

            total_beds = sum(room.bed_count for room in rooms)
            available_beds = sum(room.available_beds for room in rooms)
            occupied_beds = sum(room.occupied_beds for room in rooms)

            occupancy_rate = 0.0
            if total_beds > 0:
                occupancy_rate = (occupied_beds / total_beds) * 100

            hostel.update({
                'total_rooms': total_rooms,
                'total_beds': total_beds,
                'available_beds': available_beds,
                'occupied_beds': occupied_beds,
                'occupancy_rate': round(occupancy_rate, 2)
            })

    def action_open_gallery_images(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gallery'),
            'res_model': 'hostel.image',
            'view_mode': 'kanban,form',
            'views': [
                (self.env.ref('hostel_management.view_hostel_image_kanban').id, 'kanban'),
                (self.env.ref('hostel_management.view_hostel_image_form').id, 'form'),
            ],
            'domain': [('hostel_id', '=', self.id)],
            'context': {'default_hostel_id': self.id},
        }

    @api.depends('allocation_ids')
    def _compute_allocation_count(self):
        for hostel in self:
            hostel.allocation_count = len(hostel.allocation_ids)

    @api.depends('room_ids')
    def _compute_room_count(self):
        for hostel in self:
            hostel.room_count = len(hostel.room_ids.filtered(lambda r: r.active))

    @api.depends('room_ids', 'room_ids.floor')
    def _compute_floor_info(self):
        for hostel in self:
            active_rooms = hostel.room_ids.filtered(lambda r: r.active)
            if active_rooms:
                floors = list(set(active_rooms.mapped('floor')))
                floors.sort()
                hostel.floor_info = ', '.join(floors)
            else:
                hostel.floor_info = 'No rooms'

    @api.depends('room_ids', 'room_ids.floor')
    def _compute_floor_stats(self):
        for hostel in self:
            active_rooms = hostel.room_ids.filtered(lambda r: r.active)
            if active_rooms:
                floors = [int(floor) for floor in active_rooms.mapped('floor')]
                hostel.min_floor = min(floors) if floors else 0
                hostel.max_floor = max(floors) if floors else 0
            else:
                hostel.min_floor = 0
                hostel.max_floor = 0

    def action_view_rooms(self):
        """Show rooms for this hostel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Rooms - {self.name}',
            'res_model': 'hostel.room',
            'view_mode': 'kanban,list,form',
            'domain': [('hostel_id', '=', self.id)],
            'context': {'default_hostel_id': self.id}
        }

    def action_view_beds(self):
        """Show beds for this hostel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Beds - {self.name}',
            'res_model': 'hostel.bed',
            'view_mode': 'kanban,list,form',
            'domain': [('hostel_id', '=', self.id)],
            'context': {'default_hostel_id': self.id}
        }

    def action_view_available_beds(self):
        """Show available beds for this hostel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Available Beds - {self.name}',
            'res_model': 'hostel.bed',
            'view_mode': 'kanban,list,form',
            'domain': [('hostel_id', '=', self.id), ('status', '=', 'available')],
            'context': {'default_hostel_id': self.id}
        }

    def action_view_allocations(self):
        """Show allocations for this hostel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Allocations - {self.name}',
            'res_model': 'hostel.allocation',
            'view_mode': 'kanban,list,form',
            'domain': [('hostel_id', '=', self.id)],
            'context': {'default_hostel_id': self.id}
        }

    def action_view_rooms_by_floor(self):
        """Show rooms grouped by floor"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Rooms by Floor - {self.name}',
            'res_model': 'hostel.room',
            'view_mode': 'kanban,list,form',
            'domain': [('hostel_id', '=', self.id)],
            'context': {
                'group_by': 'floor',
                'default_hostel_id': self.id
            }
        }


class HostelRoom(models.Model):
    _name = 'hostel.room'
    _description = 'Hostel Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'hostel_id, floor, name'

    name = fields.Char(string='Room Number', required=True, tracking=True)
    hostel_id = fields.Many2one('hostel.hostel', string='Hostel', required=True, tracking=True)

    # Floor as selection field
    floor = fields.Selection([
        ('0', 'Ground Floor'),
        ('1', '1st Floor'),
        ('2', '2nd Floor'),
        ('3', '3rd Floor'),
        ('4', '4th Floor'),
        ('5', '5th Floor'),
        ('6', '6th Floor'),
        ('7', '7th Floor'),
        ('8', '8th Floor'),
        ('9', '9th Floor'),
        ('10', '10th Floor'),
        ('11', '11th Floor'),
        ('12', '12th Floor'),
        ('13', '13th Floor'),
        ('14', '14th Floor'),
        ('15', '15th Floor'),
    ], string='Floor', required=True, default='0')

    # Bed capacity as selection field
    capacity = fields.Selection([
        ('1', '1 Bed'),
        ('2', '2 Beds'),
        ('3', '3 Beds'),
        ('4', '4 Beds'),
        ('5', '5 Beds'),
        ('6', '6 Beds'),
    ], string='Bed Capacity', required=True, default='2')

    # Room type from user-created configuration
    room_type_id = fields.Many2one('room.type', string='Room Type', required=True, tracking=True)

    # Facilities from user-created configuration
    facility_ids = fields.Many2many(
        'facility.type',
        string='Room Add-ons',
        help="Optional add-ons available for this room. Options come from Hostel → Add-ons."
    )

    # Room images
    image_1920 = fields.Image(string='Room Image', max_width=1920, max_height=1920)
    image_512 = fields.Image(string="Image 512", related="image_1920", max_width=512, max_height=512, store=True)

    # Rent calculation
    base_rent_amount = fields.Float(string='Base Monthly Rent', compute='_compute_base_rent', store=True)
    rent_amount = fields.Float(string='Monthly Rent', required=True, tracking=True)

    # Room status - computed from bed statuses
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance')
    ], string='Status', compute='_compute_room_status', store=True, default='available')

    # Room-level maintenance override
    room_maintenance = fields.Boolean(
        string='Room Under Maintenance',
        default=False,
        help="If checked, the entire room is under maintenance. This overrides individual bed statuses."
    )

    # Computed field for AC status
    is_ac = fields.Boolean(
        string='AC Room',
        compute='_compute_is_ac',
        store=True,
        help="True if room has AC facility"
    )

    # Relations
    bed_ids = fields.One2many('hostel.bed', 'room_id', string='Beds')
    allocation_ids = fields.One2many('hostel.allocation', 'room_id', string='Allocations')

    # Computed fields
    bed_count = fields.Integer(string='Total Beds', compute='_compute_bed_counts', store=True)
    available_beds = fields.Integer(string='Available Beds', compute='_compute_bed_counts', store=True)
    occupied_beds = fields.Integer(string='Occupied Beds', compute='_compute_bed_counts', store=True)
    occupancy_rate = fields.Float(string='Occupancy Rate', compute='_compute_bed_counts', store=True)
    allocation_count = fields.Integer(string='Allocations', compute='_compute_allocation_count')

    allowed_addon_ids = fields.Many2many(
        'facility.type',
        compute='_compute_allowed_addons',
        string='Allowed Add-ons',
        store=False
    )

    # Active field
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('room_unique', 'unique(hostel_id, name)', 'Room number must be unique within a hostel!'),
    ]

    @api.depends('room_type_id', 'facility_ids', 'hostel_id')
    def _compute_base_rent(self):
        """Compute base rent based on hostel-specific room type and facilities"""
        for room in self:
            base_rent = 0.0
            if room.room_type_id and room.hostel_id:
                base_rent = room.hostel_id._get_room_type_rent(room.room_type_id)
            for facility in room.facility_ids:
                if room.hostel_id:
                    base_rent += room.hostel_id._get_facility_rent(facility)
            room.base_rent_amount = base_rent
            if room.rent_amount == 0 or room.rent_amount == room.base_rent_amount:
                room.rent_amount = base_rent

    @api.depends('facility_ids')
    def _compute_is_ac(self):
        """Compute if room has AC facility"""
        # Find AC facility - use exact match
        ac_facility = self.env['facility.type'].search([
            ('name', '=', 'Air Conditioner')
        ], limit=1)

        if not ac_facility:
            ac_facility = self.env['facility.type'].search([
                ('name', '=', 'AC')
            ], limit=1)

        for room in self:
            room.is_ac = ac_facility and ac_facility in room.facility_ids

    @api.depends('hostel_id')
    def _compute_allowed_addons(self):
        for room in self:
            room.allowed_addon_ids = room.hostel_id.extra_facility_ids if room.hostel_id else self.env['facility.type']

    @api.depends('bed_ids', 'bed_ids.status', 'bed_ids.active', 'room_maintenance')
    def _compute_room_status(self):
        """Compute room status based on bed statuses and room maintenance flag"""
        for room in self:
            if room.room_maintenance:
                room.status = 'maintenance'
            else:
                active_beds = room.bed_ids.filtered(lambda b: b.active)
                if not active_beds:
                    room.status = 'available'
                    continue

                available_beds = active_beds.filtered(lambda b: b.status == 'available')
                occupied_beds = active_beds.filtered(lambda b: b.status == 'occupied')
                maintenance_beds = active_beds.filtered(lambda b: b.status == 'maintenance')
                total_active_beds = len(active_beds)

                if len(occupied_beds) > 0 and len(maintenance_beds) > 0:
                    room.status = 'occupied'
                elif len(available_beds) > 0:
                    room.status = 'available'
                elif len(occupied_beds) == total_active_beds:
                    room.status = 'occupied'
                elif len(maintenance_beds) == total_active_beds:
                    room.status = 'maintenance'
                else:
                    room.status = 'occupied'

    @api.depends('bed_ids', 'bed_ids.status')
    def _compute_bed_counts(self):
        """Compute bed statistics"""
        for room in self:
            active_beds = room.bed_ids.filtered(lambda b: b.active)
            room.bed_count = len(active_beds)
            room.available_beds = len(active_beds.filtered(lambda b: b.status == 'available'))
            room.occupied_beds = len(active_beds.filtered(lambda b: b.status == 'occupied'))
            room.occupancy_rate = (room.occupied_beds / room.bed_count * 100) if room.bed_count > 0 else 0.0

    @api.depends('allocation_ids')
    def _compute_allocation_count(self):
        for room in self:
            room.allocation_count = len(room.allocation_ids)


    def action_view_beds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Beds - {self.name}',
            'res_model': 'hostel.bed',
            'view_mode': 'kanban,list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id}
        }

    def action_view_allocations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Allocations - {self.name}',
            'res_model': 'hostel.allocation',
            'view_mode': 'kanban,list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id}
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.capacity:
                record._create_beds()
        return records

    @api.onchange('room_type_id')
    def _onchange_room_type(self):
        if self.room_type_id:
            self.capacity = str(self.room_type_id.default_capacity)

    def _create_beds(self):
        for room in self:
            capacity_int = int(room.capacity)
            existing_beds = len(room.bed_ids)

            if existing_beds < capacity_int:
                for i in range(existing_beds + 1, capacity_int + 1):
                    self.env['hostel.bed'].create({
                        'name': f'{room.name}-B{i}',
                        'room_id': room.id,
                        'rent_amount': room.rent_amount,
                        'maintenance': False,
                    })

    @api.onchange('room_type_id', 'facility_ids')
    def _onchange_facilities(self):
        for room in self:
            room.rent_amount = room.base_rent_amount

    @api.constrains('facility_ids', 'hostel_id')
    def _check_room_addons_are_allowed(self):
        for room in self:
            if room.hostel_id and room.facility_ids:
                invalid = room.facility_ids - room.hostel_id.extra_facility_ids
                if invalid:
                    raise ValidationError(_(
                        "These add-ons are not enabled in the hostel: %s\n"
                        "Please enable them in Hostel → Add-ons."
                    ) % ', '.join(invalid.mapped('name')))


class HostelBed(models.Model):
    _name = 'hostel.bed'
    _description = 'Hostel Bed'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'room_id, name'

    name = fields.Char(string='Bed Number', required=True)
    room_id = fields.Many2one('hostel.room', string='Room', required=True, ondelete='cascade')
    hostel_id = fields.Many2one('hostel.hostel', string='Hostel', related='room_id.hostel_id', store=True)
    rent_amount = fields.Float(string='Monthly Rent', required=True)

    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance')
    ], string='Status', compute='_compute_status', store=True)

    maintenance = fields.Boolean(
        string='Bed Under Maintenance',
        default=False,
        help="If checked, this bed is under maintenance."
    )

    allocation_ids = fields.One2many('hostel.allocation', 'bed_id', string='Allocations')
    allocation_count = fields.Integer(
        string='Allocation Count',
        compute='_compute_allocation_count'
    )

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('bed_unique', 'unique(room_id, name)', 'Bed number must be unique within a room!'),
    ]

    @api.depends('maintenance', 'allocation_ids', 'allocation_ids.state', 'room_id.room_maintenance')
    def _compute_status(self):
        for bed in self:
            is_occupied = bed.allocation_ids and any(
                allocation.state == 'active' for allocation in bed.allocation_ids
            )

            if is_occupied:
                bed.status = 'occupied'
            elif bed.room_id.room_maintenance:
                bed.status = 'maintenance'
            elif bed.maintenance:
                bed.status = 'maintenance'
            else:
                bed.status = 'available'

    @api.depends('allocation_ids')
    def _compute_allocation_count(self):
        for bed in self:
            bed.allocation_count = len(bed.allocation_ids)

    @api.onchange('maintenance')
    def _onchange_maintenance(self):
        for bed in self:
            if bed.maintenance and bed.status == 'occupied':
                bed.maintenance = False
                return {
                    'warning': {
                        'title': _('Cannot Set Maintenance'),
                        'message': _('Cannot put an occupied bed under maintenance. Please checkout the guest first.')
                    }
                }

    def write(self, vals):
        if 'maintenance' in vals and vals['maintenance']:
            for bed in self:
                if bed.allocation_ids and any(allocation.state == 'active' for allocation in bed.allocation_ids):
                    raise UserError(_(
                        'Cannot put an occupied bed under maintenance. Please checkout the guest first.'
                    ))
        return super(HostelBed, self).write(vals)

    def action_view_allocations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Allocations - {self.name}',
            'res_model': 'hostel.allocation',
            'view_mode': 'kanban,list,form',
            'domain': [('bed_id', '=', self.id)],
            'context': {'default_bed_id': self.id}
        }
