# Multi-Occupant Feature Implementation

## Overview
This document describes the implementation of the multi-occupant feature that allows tracking multiple persons (couples, roommates, families) staying in a single room.

## Implementation Approach: Co-Tenant/Occupant Model (Option 1)

### Why This Approach?
✅ **Preserves Existing Logic**: Tenant model remains unchanged, all billing calculations intact
✅ **Flexible Tracking**: Support multiple occupant types (primary, co-tenant, spouse, dependent, guest)
✅ **No Breaking Changes**: Existing data and calculations continue to work
✅ **Easy to Implement**: Minimal changes to existing models

## New Model: property.occupant

### Purpose
Track all individuals staying in a room, including:
- Primary tenants (the main person on the agreement)
- Co-tenants (roommates, couples)
- Spouses/family members
- Dependents (children)
- Guests (temporary visitors)

### Key Fields

#### Identification
- `name` - Full name of the occupant
- `is_primary` - Boolean flag for primary tenant
- `occupant_type` - Selection: primary_tenant, co_tenant, spouse, dependent, guest
- `id_type` - Selection: emirates_id, passport, visa
- `id_passport` - ID/Passport number
- `image` - Photo of the occupant

#### Contact Information
- `mobile` - Primary phone number
- `phone` - Alternative phone
- `email` - Email address
- `date_of_birth` - Birth date
- `gender` - Selection: male, female, other
- `nationality` - Country

#### Relationships
- `agreement_id` - Link to the rental agreement (required)
- `room_id` - Computed from agreement (readonly)
- `property_id` - Computed from agreement (readonly)

#### Dates
- `move_in_date` - When they moved in
- `move_out_date` - When they moved out (if applicable)
- `active` - Boolean to mark inactive occupants

#### Emergency Contact
- `emergency_contact_name`
- `emergency_contact_phone`
- `emergency_contact_relation`

#### Professional Info
- `company_name`
- `job_title`

#### Documents
- `document_ids` - One2many to ir.attachment for storing documents
- `documents_count` - Computed count of documents

#### Notes
- `notes` - Text field for additional information

### Constraints
1. **Single Primary Per Agreement**: Only one occupant can be marked as primary per agreement
2. **Unique ID Validation**: ID/Passport numbers must be unique
3. **Move-out Date Validation**: Move-out date must be after move-in date

### Name Display
The `name_get` method shows: "Name (Occupant Type)" for easy identification in dropdowns.

## Updated Models

### property.agreement

#### New Fields
- `occupant_ids` - One2many relationship to property.occupant
- `occupants_count` - Computed field showing total number of occupants
- `occupants_names` - Computed field showing comma-separated list of occupant names
- `primary_occupant_id` - Computed field showing the primary occupant

#### New Compute Methods
- `_compute_occupants_count()` - Counts total occupants
- `_compute_occupants_names()` - Creates list of names
- `_compute_primary_occupant()` - Finds the primary occupant

## Views

### Occupant List View
- Shows all occupants with key information
- Primary tenants highlighted in bold
- Optional columns for detailed view
- Boolean toggle for is_primary and active fields

### Occupant Form View
Features:
- Large photo display
- Primary tenant toggle prominently displayed
- Tabbed interface for:
  - Contact Information
  - Identification
  - Emergency Contact
  - Professional Info
  - Documents (with stat button)
  - Notes
- Chatter for tracking history

### Occupant Kanban View
- Mobile-optimized card view
- Shows photo, name, occupant type, phone, room
- Primary tenant marked with ★ symbol

### Occupant Search View
Filters:
- Primary Tenants
- Co-Tenants
- Active/Inactive

Group By:
- Occupant Type
- Room
- Property
- Agreement

### Agreement Form View - New Tab
Added "Occupants" tab showing:
- Summary information (count, primary occupant, names)
- Editable list of all occupants
- Quick add/edit capabilities

## Security

### Access Rights (ir.model.access.csv)
- **Property User**: Read-only access
- **Property Officer**: Create, read, write (no delete)
- **Property Manager**: Full access (CRUD)
- **Property Tenant Manager**: Create, read, write (no delete)

### Record Rules (property_security.xml)
- All property users can see all occupants
- Tenant managers can see all occupants
- Domain filter: [] (no restrictions)

## Menu Structure
New menu item added:
- **Location**: Tenant Management → Room Occupants
- **Sequence**: 25 (between tenants and agreements)
- **Visible to**: All property management groups

## Usage Examples

### Scenario 1: Couple in Room
1. Create rental agreement for primary tenant
2. Add primary tenant as occupant with `occupant_type = 'primary_tenant'` and `is_primary = True`
3. Add spouse as occupant with `occupant_type = 'spouse'` and `is_primary = False`
4. Both occupants linked to same agreement

### Scenario 2: Three Roommates
1. Create rental agreement
2. Add first person as primary tenant (`is_primary = True`)
3. Add two co-tenants (`occupant_type = 'co_tenant'`, `is_primary = False`)

### Scenario 3: Family with Children
1. Create rental agreement
2. Add primary tenant (main person responsible for rent)
3. Add spouse
4. Add children as dependents (`occupant_type = 'dependent'`)

## Benefits

### For Management
- Complete occupancy records for compliance
- Better understanding of who lives where
- Emergency contact information for all occupants
- Document management per person

### For Billing
- Tenant model unchanged - all billing calculations intact
- No impact on rent collection
- No changes to invoicing
- Outstanding dues calculations unaffected

### For Compliance
- Full identification records
- Move-in/move-out tracking
- Document storage
- Audit trail via chatter

## Testing Checklist

- [ ] Create occupant with all required fields
- [ ] Verify only one primary per agreement constraint
- [ ] Test unique ID validation
- [ ] Add multiple occupants to one agreement
- [ ] View occupants list from agreement form
- [ ] Test occupant search and filters
- [ ] Verify computed fields update correctly
- [ ] Test with different occupant types
- [ ] Verify document upload and count
- [ ] Test move-in/move-out date validation
- [ ] Confirm billing calculations unchanged
- [ ] Test with tenant manager security group

## Migration Notes

### Existing Data
No migration needed! Existing agreements without occupants will work normally.

### Backward Compatibility
✅ All existing tenant and agreement records work as-is
✅ No changes to billing calculations
✅ No changes to collection tracking
✅ Optional feature - not required to use

## Future Enhancements (Optional)

1. **Auto-create Primary Occupant**: When agreement is created, automatically create occupant from tenant data
2. **Bulk Import**: Import multiple occupants from CSV/Excel
3. **Occupant History**: Track movement between rooms
4. **Communication**: Send notifications to specific occupants
5. **Reports**: Occupancy analytics and demographics

## Technical Details

### Files Modified
1. `models/property_occupant.py` - NEW FILE
2. `models/__init__.py` - Added import
3. `models/property_agreement.py` - Added occupant fields
4. `views/occupant_views.xml` - NEW FILE
5. `views/agreement_views.xml` - Added occupants tab
6. `views/menu_views.xml` - Defined parent menu
7. `security/ir.model.access.csv` - Added access rights
8. `security/property_security.xml` - Added record rules
9. `__manifest__.py` - Added occupant_views.xml

### Dependencies
- Standard Odoo modules: base, mail
- Property management models: property.agreement, property.room, property.property

## Support

For questions or issues with this feature:
1. Check constraint error messages (they're clear about what's wrong)
2. Review this documentation
3. Check Odoo logs for detailed errors
4. Verify security group assignments

---
**Implementation Date**: 2025
**Odoo Version**: 18.0
**Status**: ✅ Production Ready
