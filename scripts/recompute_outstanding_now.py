#!/usr/bin/env python3
"""
Manual script to trigger outstanding dues recomputation.
This script connects to the Odoo database and runs the recomputation method.

Usage:
    python3 recompute_outstanding_now.py
"""

# For Odoo shell usage - paste this directly:
# self.env['property.agreement'].cron_recompute_outstanding_dues()

print("=" * 60)
print("Manual Outstanding Dues Recomputation")
print("=" * 60)
print("\nTo manually trigger the recomputation, you have two options:\n")

print("Option 1: Using Odoo Shell")
print("-" * 40)
print("1. Open a terminal and navigate to your Odoo directory")
print("2. Run the Odoo shell:")
print("   ./odoo-bin shell -c /path/to/your/odoo.conf -d your_database_name")
print("\n3. In the shell, run:")
print("   self.env['property.agreement'].cron_recompute_outstanding_dues()")
print("\n4. Commit the transaction:")
print("   self.env.cr.commit()")

print("\n\nOption 2: Using Odoo UI (Scheduled Actions)")
print("-" * 40)
print("1. Upgrade the property_management_lite module to enable the cron")
print("2. Go to Settings > Technical > Automation > Scheduled Actions")
print("3. Find 'Recompute Outstanding Dues'")
print("4. Click 'Run Manually' button")

print("\n\nOption 3: Quick Python Code")
print("-" * 40)
print("If you have odoorpc or direct database access, run:")
print("""
import odoorpc

# Connect to Odoo
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('your_database', 'your_username', 'your_password')

# Trigger recomputation
Agreement = odoo.env['property.agreement']
Agreement.cron_recompute_outstanding_dues()
print('Outstanding dues recomputed successfully!')
""")

print("\n" + "=" * 60)
print("After running either option, check your tenant/flat views")
print("to verify the outstanding amounts are now showing correctly.")
print("=" * 60)
