# odoo18-hostel-management

An Odoo 18 module for complete hostel and PG (Paying Guest) management — covering rooms, beds, tenant onboarding, allocations, invoicing, security deposits, and a tenant portal.

Built on Odoo 18 Community. Tested with the Accounting, Contacts, and Portal apps.

---

## What It Does

- Manages multiple hostels and PGs under one company, each with its own rooms, beds, facilities, and services
- Tracks bed-level occupancy with automatic status updates (Available → Occupied → Under Maintenance)
- Onboards tenants with personal info, ID proof, academic details, emergency contacts, and a profile photo
- Handles the full allocation lifecycle: Draft → Active → Checked Out → Cancelled
- Generates monthly rent invoices automatically via a scheduled cron job
- Manages security deposits end-to-end: invoice → receive → refund via credit note
- Gives tenants portal access to view their allocation, invoices, and payment history
- Provides a dashboard with occupancy charts across all hostels

---

## Screenshots

### Dashboard — Occupancy by Hostel
![Dashboard](static/src/img/screenshots/dashboard.png)

### Hostel Record — Rooms, Beds, Facilities
![Hostel record](static/src/img/screenshots/hostel_record.png)

### Rooms by Floor — Availability and Status
![Rooms by floor](static/src/img/screenshots/rooms_by_floor.png)

### Room — Occupancy Rate and Add-ons
![Room detail](static/src/img/screenshots/room_detail.png)

### Bed — Status and Allocation History
![Bed detail](static/src/img/screenshots/bed_detail.png)

### Tenant Profile — Personal Info and Portal Access
![Tenant profile](static/src/img/screenshots/tenant_profile.png)

### Active Allocations — Kanban View
![Active allocations](static/src/img/screenshots/active_allocations.png)

### Allocation — Billing Info with Services and Deposit
![Allocation billing](static/src/img/screenshots/allocation_billing.png)

### Allocation — Payment Info and Deposit Movement
![Allocation payment](static/src/img/screenshots/allocation_payment.png)

### Security Deposit — Invoice and Ledger
![Security deposit](static/src/img/screenshots/security_deposit.png)

### Invoice List — Monthly Rent Invoices
![Invoice list](static/src/img/screenshots/invoice_list.png)

---

## Key Features

### Hostel & Room Management
- Hostel and PG types with contact details, address, and photo gallery
- Rooms organized by floor with room type (Single/Double/Triple/Dormitory), bed count, and add-on facilities
- Rooms display Available / Occupied / Maintenance status with bed capacity and rent
- Facility types (AC, WiFi, Attached Bathroom, Microwave) and service types (GYM, Mess, Parking) configured per hostel
- Room add-on rates and service charges configured under Rent Configuration

### Tenant Management
- Tenant records with personal info, academic info, emergency contacts, and ID proof
- Portal access — invite tenant, re-send invite, revoke access
- Payment info tab showing total paid, outstanding, next payment date

### Allocation Lifecycle
- Preferred room type and AC type captured at allocation
- Check-in and expected check-out dates with duration tracking
- Active, Checked Out, and Cancelled states
- Full allocation history per bed

### Billing and Invoicing
- Monthly rent + services charge calculated automatically per allocation
- Security deposit invoiced separately, tracked with received/refunded amounts
- Invoice list filtered by hostel with GST support (SGST + CGST)
- Payment status shown on allocation: Paid / Partially Paid / Outstanding

---

## Configuration

| Menu | What to Set Up |
|---|---|
| Configuration → Room Types | Single Sharing, Double Sharing, Triple Sharing, Dormitory |
| Configuration → Facility Types | AC, WiFi, Attached Bathroom, etc. |
| Configuration → Service Types | GYM, Mess, Parking, etc. |
| Hostel → Rent Configuration | Add-on rates and service charges per hostel |

---

## Install

Requires Odoo 18 Community with `account`, `portal`, and `contacts` installed.

1. Clone the repo into your addons folder:
   ```bash
   git clone https://github.com/mayuri2392/odoo18-hostel-management.git \
     ~/Projects/odoo18/custom_addons/hostel_management
   ```
2. Restart Odoo
3. Go to **Settings → Apps**, search for `hostel_management` → Install

---

## Author

**Mayuri Patil**
Odoo Functional + Technical Consultant
[LinkedIn](https://linkedin.com/in/mayuri-patil-2392) · [GitHub](https://github.com/mayuri2392)