#!/usr/bin/env python3
"""
Diagnostic script to check why outstanding dues are not being calculated.

This script helps debug the outstanding calculation by checking:
1. Agreement state and dates
2. Collections data
3. Computed field values
4. Calculation logic

Run this in Odoo shell:
./odoo-bin shell -c /path/to/odoo.conf -d your_database

Then paste and run the code below.
"""

print("=" * 70)
print("OUTSTANDING DUES DIAGNOSTIC")
print("=" * 70)

# Find the tenant
tenant = self.env['property.tenant'].search([('name', 'ilike', 'FRBIN')], limit=1)

if not tenant:
    print("\n❌ Tenant 'FRBIN' not found!")
else:
    print(f"\n✅ Found Tenant: {tenant.name} (ID: {tenant.id})")
    
    # Check current agreement
    print(f"\n{'='*70}")
    print("CURRENT AGREEMENT CHECK")
    print(f"{'='*70}")
    
    if not tenant.current_agreement_id:
        print("❌ No current_agreement_id set on tenant!")
        print("\nSearching for active agreements...")
        agreements = tenant.agreement_ids.filtered(lambda a: a.state == 'active')
        if agreements:
            print(f"✅ Found {len(agreements)} active agreement(s):")
            for agr in agreements:
                print(f"   - Agreement ID: {agr.id}, State: {agr.state}")
        else:
            print("❌ No active agreements found!")
    else:
        agreement = tenant.current_agreement_id
        print(f"✅ Current Agreement ID: {agreement.id}")
        print(f"   State: {agreement.state}")
        print(f"   Start Date: {agreement.start_date}")
        print(f"   End Date: {agreement.end_date}")
        print(f"   Monthly Rent: {agreement.rent_amount}")
        
        # Check collections
        print(f"\n{'='*70}")
        print("COLLECTIONS CHECK")
        print(f"{'='*70}")
        
        collections = agreement.collection_ids.filtered('active')
        print(f"Total active collections: {len(collections)}")
        
        if collections:
            total_collected = sum(collections.mapped('amount_collected'))
            print(f"Total amount collected: {total_collected}")
            for col in collections[:5]:  # Show first 5
                print(f"   - Date: {col.date}, Amount: {col.amount_collected}, Type: {col.collection_type}")
        else:
            print("ℹ️  No collections recorded yet")
        
        # Check computed values
        print(f"\n{'='*70}")
        print("COMPUTED VALUES ON AGREEMENT")
        print(f"{'='*70}")
        
        print(f"Total Collected: {agreement.total_collected}")
        print(f"Pending Amount: {agreement.pending_amount}")
        print(f"Last Payment Date: {agreement.last_payment_date}")
        
        # Manual calculation
        print(f"\n{'='*70}")
        print("MANUAL CALCULATION")
        print(f"{'='*70}")
        
        from dateutil.relativedelta import relativedelta
        from odoo import fields
        
        today = fields.Date.today()
        start_date = agreement.start_date
        
        print(f"Today: {today}")
        print(f"Start Date: {start_date}")
        
        delta = relativedelta(today, start_date)
        complete_months = delta.years * 12 + delta.months
        
        print(f"Years: {delta.years}, Months: {delta.months}")
        print(f"Complete months: {complete_months}")
        
        expected_amount = agreement.rent_amount * complete_months
        print(f"Expected amount: {agreement.rent_amount} × {complete_months} = {expected_amount}")
        
        actual_pending = max(0, expected_amount - agreement.total_collected)
        print(f"Calculated pending: {expected_amount} - {agreement.total_collected} = {actual_pending}")
        
        if agreement.pending_amount != actual_pending:
            print(f"\n⚠️  MISMATCH! Agreement.pending_amount ({agreement.pending_amount}) != Calculated ({actual_pending})")
        else:
            print(f"\n✅ Values match!")
    
    # Check tenant outstanding fields
    print(f"\n{'='*70}")
    print("TENANT OUTSTANDING FIELDS")
    print(f"{'='*70}")
    
    print(f"Rent Outstanding: {tenant.rent_outstanding}")
    print(f"Deposit Outstanding: {tenant.deposit_outstanding}")
    print(f"Parking Outstanding: {tenant.parking_outstanding}")
    print(f"Total Outstanding: {tenant.total_outstanding_dues}")
    print(f"Outstanding Status: {tenant.outstanding_status}")
    
    # Check flat outstanding
    if tenant.current_flat_id:
        print(f"\n{'='*70}")
        print("FLAT OUTSTANDING")
        print(f"{'='*70}")
        print(f"Flat: {tenant.current_flat_id.name}")
        print(f"Total Outstanding Dues: {tenant.current_flat_id.total_outstanding_dues}")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print("\nTo force recomputation, run:")
print("agreement._compute_payment_stats()")
print("tenant._compute_outstanding_dues()")
print("self.env.cr.commit()")
