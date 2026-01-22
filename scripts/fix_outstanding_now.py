"""
IMMEDIATE FIX - Run this in Odoo Shell to update outstanding amounts NOW

Run Odoo shell:
    cd /path/to/odoo
    ./odoo-bin shell -c /path/to/odoo.conf -d your_database

Then paste and execute this code:
"""

# Recompute outstanding for all active agreements
agreements = self.env['property.agreement'].search([('state', '=', 'active')])
print(f"Recomputing {len(agreements)} active agreements...")
agreements._compute_payment_stats()

# Recompute outstanding for all active tenants (THIS WAS MISSING!)
tenants = self.env['property.tenant'].search([('active', '=', True)])
print(f"Recomputing {len(tenants)} active tenants...")
tenants._compute_outstanding_dues()

# Recompute all flats
flats = self.env['property.flat'].search([])
print(f"Recomputing {len(flats)} flats...")
flats._compute_financial_summary()

# Commit the changes
self.env.cr.commit()
print("✅ Done! Refresh your browser to see the updated values.")
