# Auto-Post Invoices Configuration

## What Was Changed

### 1. Default Setting Updated
Changed the default value for `auto_post_invoices` in the agreement model:
- **Before**: `default=False` (invoices created as draft)
- **After**: `default=True` (invoices automatically confirmed/posted)

**File**: `models/property_agreement.py`

### 2. Impact
- **New agreements** created from now on will have auto-post enabled by default
- **Existing agreements** need to be updated (see step 3)

### 3. Update Existing Agreements

Run this script in Odoo shell to enable auto-post for all existing agreements:

```python
exec(open('Custom_Addons/property_management_lite/scripts/enable_auto_post_invoices.py').read())
```

This will:
- Find all existing agreements (675 agreements)
- Enable `auto_post_invoices` for each one
- Commit the changes

## How It Works

### Invoice Generation Process
1. **Cron Job Runs**: "Property Management: Generate Monthly Invoices" (scheduled action)
2. **Finds Agreements**: All active agreements with `auto_generate_invoices = True`
3. **Creates Invoices**: For agreements where invoice day has arrived
4. **Auto-Posts**: If `auto_post_invoices = True`, the invoice is automatically confirmed

### Code Flow
```python
# In models/property_invoice.py
def _create_monthly_invoice(self, agreement, invoice_date):
    # ... create invoice ...
    
    # Auto-post if configured
    if agreement.auto_post_invoices:
        invoice.action_post()  # This confirms the invoice
```

## Verification

### Check Agreement Settings
1. Go to **Tenant Management → Agreements**
2. Open any agreement
3. Check the **Invoicing Automation** section:
   - ✅ Auto Generate Invoices: Should be checked
   - ✅ Auto Post Invoices: Should be checked (after running the script)

### Test Invoice Generation
1. Go to **Settings → Technical → Automation → Scheduled Actions**
2. Find "Property Management: Generate Monthly Invoices"
3. Click **Run Manually**
4. Check **Accounting → Customers → Invoices**
5. New invoices should be in **Posted** state (not Draft)

## Manual Control

### Per Agreement
You can still control this per agreement:
- Edit an agreement
- Uncheck "Auto Post Invoices" if you want to review invoices before posting
- Invoices for that agreement will be created as drafts

### Global Setting
To disable auto-post for all new agreements:
- Edit `models/property_agreement.py`
- Change `auto_post_invoices = fields.Boolean(..., default=False)`
- Restart Odoo

## Benefits of Auto-Post

✅ **Saves Time**: No need to manually confirm hundreds of invoices
✅ **Consistency**: All invoices are posted on the same day
✅ **Automation**: Fully automated rent collection process
✅ **Accounting**: Posted invoices immediately update accounting records
✅ **Reports**: Posted invoices appear in financial reports immediately

## Rollback (If Needed)

If you want to go back to draft invoices:

1. **For existing agreements**:
```python
# In Odoo shell:
env['property.agreement'].search([]).write({'auto_post_invoices': False})
env.cr.commit()
```

2. **For new agreements**:
   - Change `default=True` back to `default=False` in `models/property_agreement.py`
   - Restart Odoo

## Summary

✅ **Default changed**: New agreements will auto-post invoices
📝 **Script provided**: Update existing agreements with one command
🎯 **Result**: Fully automated invoice generation and posting
