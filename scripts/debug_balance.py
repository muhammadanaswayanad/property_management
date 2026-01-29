from odoo import env, fields

def inspect_balances(tenant_name_part):
    tenant = env['property.tenant'].search([('name', 'ilike', tenant_name_part)], limit=1)
    if not tenant:
        print(f"Tenant not found matching '{tenant_name_part}'")
        return

    print(f"Inspecting statements for tenant: {tenant.name} (ID: {tenant.id})")
    
    statements = env['property.statement'].search([
        ('tenant_id', '=', tenant.id)
    ], order='transaction_date asc, id asc')
    
    cumulative = 0.0
    print(f"{'ID':<5} | {'Date':<10} | {'Type':<12} | {'Debit':<10} | {'Credit':<10} | {'Stored Bal':<10} | {'Calc Bal':<10} | {'Ref'}")
    print("-" * 90)
    
    for stmt in statements:
        cumulative += stmt.debit_amount - stmt.credit_amount
        print(f"{stmt.id:<5} | {str(stmt.transaction_date):<10} | {stmt.transaction_type:<12} | {stmt.debit_amount:<10.2f} | {stmt.credit_amount:<10.2f} | {stmt.running_balance:<10.2f} | {cumulative:<10.2f} | {stmt.reference}")

# Run for the tenant "MADAN" seen in screenshot
inspect_balances('MADAN')
