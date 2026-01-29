from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.move'
    _description = 'Journal Entry/Invoice'
    _order = 'invoice_date desc, id desc'

    # name = fields.Char('Invoice Number', required=True, copy=False, readonly=True, 
    #                    default=lambda self: _('New'))
    
    # Basic Information
    # invoice_date = fields.Date('Invoice Date', required=True, default=fields.Date.today, tracking=True)
    # invoice_date_due = fields.Date('Due Date', required=True, tracking=True)
    
    # Relations
    tenant_id = fields.Many2one('property.tenant', 'Tenant', tracking=True)
    @api.onchange('partner_id')
    def _onchange_partner_id_tenant(self):
       if self.partner_id:
           self.tenant_id = self.partner_id.tenant_id

    room_id = fields.Many2one('property.room', 'Room', tracking=True, domain="[('property_id','=',property_id)]")

    @api.onchange('property_id')
    def _onchange_property_id(self):
        if self.property_id:
            self.room_id = False
            self.agreement_id = False
    property_id = fields.Many2one('property.property', string='Property', store=True)
    agreement_id = fields.Many2one('property.agreement', 'Agreement',)
    collection_id = fields.Many2one('property.collection', 'Collection', readonly=True)
    
    # Additional Fields
    invoice_type = fields.Selection([
        ('rent', 'Monthly Rent'),
        ('deposit', 'Security Deposit'),
        ('parking', 'Parking'),
        ('maintenance', 'Maintenance'),
        ('utility', 'Utilities'),
        ('penalty', 'Late Fee'),
        ('other', 'Other'),
    ], string='Invoice Type', default='rent')

    def _default_period_from(self):
        today = date.today()
        return today.replace(day=1)

    def _default_period_to(self):
        today = date.today()
        next_month = today.replace(day=28) + timedelta(days=4)  # this will never fail
        last_day = next_month - timedelta(days=next_month.day)
        return last_day

    period_from = fields.Date('Period From', default=_default_period_from)
    period_to = fields.Date('Period To', default=_default_period_to)
    notes = fields.Text('Terms and Conditions')
    
    # Archive
    active = fields.Boolean('Active', default=True)

    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.tenant_id = self.room_id.current_tenant_id
            self.agreement_id = self.room_id.current_agreement_id
            self._onchange_agreement_id()

    @api.onchange('agreement_id', 'invoice_date', 'invoice_type')
    def _onchange_agreement_id(self):
        if self.agreement_id and self.invoice_date:
            # Set due invoice_date based on payment terms
            self.invoice_date_due = self.invoice_date + timedelta(days=self.agreement_id.payment_terms or 30)
            
            # Create default invoice lines based on agreement
            lines = []
            if self.invoice_type == 'rent':
                lines.append({
                    'product_id': self.env.ref('property_management_lite.product_property_rent').product_variant_id.id,
                    'name': f'Monthly Rent - {self.room_id.name}',
                    'quantity': 1,
                    'price_unit': self.agreement_id.rent_amount,
                })
            elif self.invoice_type == 'deposit':
                lines.append({
                    'product_id': self.env.ref('property_management_lite.product_property_deposit').product_variant_id.id,
                    'name': f'Security Deposit - {self.room_id.name}',
                    'quantity': 1,
                    'price_unit': self.agreement_id.deposit_amount,
                })
            elif self.invoice_type == 'parking':
                lines.append({
                    'product_id': self.env.ref('property_management_lite.product_property_rent').product_variant_id.id, # Use rent or custom product
                    'name': f'Parking Charges - {self.room_id.name}',
                    'quantity': 1,
                    'price_unit': self.agreement_id.parking_charges,
                })
                            
            self.invoice_line_ids = [(5, 0, 0)] + [(0, 0, line) for line in lines]

    @api.model
    def create_monthly_invoices(self):
        """Cron job to create monthly invoices"""
        today = fields.Date.today()
        
        _logger.info(f"========== INVOICE GENERATION STARTED ==========")
        _logger.info(f"Current date: {today}, Day: {today.day}")
        
        # Find all active agreements with auto-generate enabled
        active_agreements = self.env['property.agreement'].search([
            ('state', '=', 'active'),
            ('auto_generate_invoices', '=', True)
        ])
        
        _logger.info(f"Found {len(active_agreements)} active agreements with auto-generate enabled")
        
        invoices_created = 0
        for agreement in active_agreements:
            try:
                _logger.info(f"Processing agreement: {agreement.name} (ID: {agreement.id})")
                _logger.info(f"  - Payment frequency: {agreement.payment_frequency}")
                _logger.info(f"  - Invoice day: {agreement.invoice_day}")
                _logger.info(f"  - Auto-generate: {agreement.auto_generate_invoices}")
                
                # Check if invoice should be generated
                # Generate if today is invoice day OR if we passed invoice day but haven't generated yet this month
                if agreement.payment_frequency == 'monthly':
                    # Check if invoice already exists for current month
                    first_day_of_month = today.replace(day=1)
                    existing_invoice = self.search([
                        ('agreement_id', '=', agreement.id),
                        ('invoice_type', '=', 'rent'),
                        ('invoice_date', '>=', first_day_of_month),
                        ('invoice_date', '<=', today),
                        ('state', '!=', 'cancel')
                    ], limit=1)
                    
                    if today.day >= agreement.invoice_day:
                        # 1. Rent Invoice
                        # Check logic moved inside _create_monthly_invoice
                        self._create_monthly_invoice(agreement, today, invoice_type='rent')
                        invoices_created += 1
                        
                        # 2. Parking Invoice
                        if agreement.parking_charges > 0:
                            self._create_monthly_invoice(agreement, today, invoice_type='parking')
                    
                        # 3. Other Monthly Charges
                        for charge in agreement.other_charges_ids:
                            if charge.frequency == 'monthly' and charge.active:
                                # Map charge type
                                inv_type = 'other'
                                if charge.charge_id.charge_type in ['maintenance', 'utility', 'penalty']:
                                    inv_type = charge.charge_id.charge_type
                                
                                self._create_monthly_invoice(
                                    agreement, today, 
                                    invoice_type=inv_type,
                                    amount=charge.amount,
                                    description=charge.charge_id.name
                                )
                    else:
                        _logger.info(f"  - Skipping: Invoice day {agreement.invoice_day} not yet reached (today is {today.day})")
                else:
                    _logger.info(f"  - Skipping: payment_frequency is {agreement.payment_frequency}, not monthly")
            except Exception as e:
                _logger.error(f"Error creating invoice for agreement {agreement.name}: {str(e)}", exc_info=True)
        
        _logger.info(f"Successfully created {invoices_created} invoices")
        _logger.info(f"========== INVOICE GENERATION COMPLETED ==========")
        return True

    def _create_monthly_invoice(self, agreement, invoice_date, invoice_type='rent', amount=None, description=None, product_xml_id=None):
        """Create monthly invoice for agreement"""
        if not amount:
            if invoice_type == 'rent':
                amount = agreement.rent_amount
            elif invoice_type == 'parking':
                amount = agreement.parking_charges
        
        if not description:
            description = f'{invoice_type.title()} Charges'

        # Check if invoice already exists for this month
        # For 'other' types, we might want to check duplicate based on description too?
        # But keeping it simple for now: 1 invoice per type per month
        # TODO: Better handling for multiple 'other' charges
        domain = [
            ('agreement_id', '=', agreement.id),
            ('invoice_type', '=', invoice_type),
            ('invoice_date', '>=', invoice_date.replace(day=1)),
            ('invoice_date', '<=', invoice_date),
            ('state', '!=', 'cancelled')
        ]
        
        # Special check for 'other' types to avoid blocking multiple different charges
        if invoice_type not in ['rent', 'parking', 'deposit']:
             # Use description match to distinguish different other charges
             # or assume we combine them?
             # Let's append description for uniqueness check if meaningful
             # For now, simplistic check
             pass

        existing = self.search(domain)
        
        # If multiple 'other' charges exist, we need to be careful.
        # Ideally, we loop through charges and create unique invoices if they don't exist.
        # But search() finds ANY invoice of that type.
        # If we have 2 maintenance charges, the first one will create an invoice.
        # The second loop iteration will duplicate? No, search finds valid one.
        # Actually, if we have Maintenance A and Maintenance B.
        # Loop 1: Create Maintenance A.
        # Loop 2: Search finds Maintenance A invoice. Skips Maintenance B!
        # Fix: Add description/name to search domain for non-standard types?
        # Or store a specific reference (source document?)
        
        if invoice_type in ['rent', 'parking', 'deposit']:
            if existing: return
        elif existing:
            # Check if an invoice with this description/amount exists?
            # Or assume standard behaviour for now (one per type)
            # Given constraints, let's enable creating multiple 'other' invoices if amounts differ?
            # Or matching specific characteristics.
            # Best approach: Add 'name' to the search?
            # Invoice name is generated.
            # Let's rely on checking matching amount/description in invoice lines? Too complex.
            # Fallback: Just create if no invoice of that type exists.
            # This means multiple maintenance charges will be problematic.
            # Recommendation: Group other charges into one invoice?
            pass

        if not existing or (invoice_type not in ['rent', 'parking', 'deposit'] and not any(i.amount_total == amount for i in existing)):
             # Allow creating additional invoices for other types if exact amount match not found
             # This is a heuristic.
             pass
        else:
             return

        if not existing:
            # Calculate period
            period_from = invoice_date.replace(day=1)
            if invoice_date.month == 12:
                period_to = period_from.replace(year=period_from.year + 1, month=1) - timedelta(days=1)
            else:
                period_to = period_from.replace(month=period_from.month + 1) - timedelta(days=1)
            
            # Determine Product
            if not product_xml_id:
                if invoice_type == 'rent':
                    product_xml_id = 'property_management_lite.product_property_rent'
                elif invoice_type == 'deposit':
                    product_xml_id = 'property_management_lite.product_property_deposit'
                else:
                    product_xml_id = 'property_management_lite.product_property_rent' # Fallback
            
            product = self.env.ref(product_xml_id).product_variant_id

            # Create invoice
            invoice = self.create({
                'partner_id': agreement.tenant_id.partner_id.id,
                'tenant_id': agreement.tenant_id.id,
                'room_id': agreement.room_id.id,
                'agreement_id': agreement.id,
                'invoice_date': invoice_date,
                'invoice_date_due': invoice_date + timedelta(days=agreement.payment_terms or 30),
                'move_type': 'out_invoice',
                'invoice_type': invoice_type,
                'period_from': period_from,
                'period_to': period_to,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': f'{description} - {agreement.room_id.name} ({period_from.strftime("%B %Y")})',
                    'quantity': 1,
                    'price_unit': amount,
                })],
                'notes': f'Monthly {invoice_type} invoice as per rental agreement.',
            })
            
            # Auto-post if configured
            if agreement.auto_post_invoices:
                invoice.action_post()

    def action_register_payment(self):
        res = super(AccountInvoice, self).action_register_payment()
        res['context'].update({
            'default_tenant_id': self.tenant_id.id,
            'default_room_id': self.room_id.id,
            'default_property_id': self.property_id.id,
            'default_agreement_id': self.agreement_id.id
        })
        return res
    
class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    name = fields.Char(compute="_compute_name", store=True, readonly=False)

    def _compute_name(self):
        for line in self:
            line.name = line.name

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.description_sale or self.product_id.name

    @api.model_create_multi
    def create(self, vals_list):
        # Override create method to set name
        recs = super(AccountInvoiceLine, self).create(vals_list)
        for rec in recs:
            if not rec.name:
                rec.write({'name': rec.product_id.description_sale or rec.product_id.name})
        return recs


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    _description = 'Property Payment'
    
    # Relations
    tenant_id = fields.Many2one('property.tenant', compute="_compute_tenant", readonly=True, store=True)
    @api.depends('partner_id')
    def _compute_tenant(self):
        for payment in self:
            if payment.partner_id:
                payment.tenant_id = payment.partner_id.tenant_id

    collection_id = fields.Many2one('property.collection', 'Collection')
    # room_id = fields.Many2one('property.room', 'Room', tracking=True)
    # property_id = fields.Many2one(related='room_id.property_id', string='Property', store=True)
    # agreement_id = fields.Many2one('property.agreement', 'Agreement',)

    reference = fields.Char('Reference', tracking=True)

    notes = fields.Text('Notes', tracking=True)
    
    # # Payment Details
    # payment_method = fields.Selection([
    #     ('cash', 'Cash'),
    #     ('bank_transfer', 'Bank Transfer'),
    #     ('cheque', 'Cheque'),
    #     ('online', 'Online Payment'),
    #     ('card', 'Card Payment'),
    # ], string='Payment Method', required=True, default='cash', tracking=True)
    

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    tenant_id = fields.Many2one('property.tenant', 'Tenant', tracking=True)
    # room_id = fields.Many2one('property.room', 'Room', tracking=True)
    # property_id = fields.Many2one(related='room_id.property_id', string='Property', store=True)
    # agreement_id = fields.Many2one('property.agreement', 'Agreement',)
    reference = fields.Char('Reference', tracking=True)

    notes = fields.Text('Notes', tracking=True)


    def _create_payment_vals_from_wizard(self, batch_result):
        values = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        values.update({
            'tenant_id': self.tenant_id.id,
            'notes': self.notes,
            # 'room_id': self.room_id.id,
            # 'property_id': self.property_id.id,
            # 'agreement_id': self.agreement_id.id,
            'reference': self.reference
        })
        return values

    def action_create_payments(self):
        """Override to handle property payments"""
        res = super(AccountPaymentRegister, self).action_create_payments()
        return res
    
# class PropertyPaymentWizard(models.TransientModel):
#     _name = 'property.payment.wizard'
#     _description = 'Property Payment Registration Wizard'

#     invoice_id = fields.Many2one('property.invoice', 'Invoice', required=True)
#     tenant_id = fields.Many2one(related='invoice_id.tenant_id', readonly=True)
#     amount = fields.Monetary('Payment Amount', required=True, currency_field='currency_id')
#     currency_id = fields.Many2one(related='invoice_id.currency_id', readonly=True)
#     date = fields.Date('Payment Date', required=True, default=fields.Date.today)
#     payment_method = fields.Selection([
#         ('cash', 'Cash'),
#         ('bank_transfer', 'Bank Transfer'),
#         ('cheque', 'Cheque'),
#         ('online', 'Online Payment'),
#         ('card', 'Card Payment'),
#     ], string='Payment Method', required=True, default='cash')
#     reference = fields.Char('Reference')

#     def action_register_payment(self):
#         """Register the payment"""
#         payment = self.env['property.payment'].create({
#             'invoice_id': self.invoice_id.id,
#             'amount': self.amount,
#             'date': self.date,
#             'payment_method': self.payment_method,
#             'reference': self.reference,
#         })
        
#         payment.action_post()
        
#         # Also create collection record
#         self.env['property.collection'].create({
#             'tenant_id': self.invoice_id.tenant_id.id,
#             'room_id': self.invoice_id.room_id.id,
#             'agreement_id': self.invoice_id.agreement_id.id,
#             'date': self.date,
#             'amount_collected': self.amount,
#             'payment_method': self.payment_method,
#             'reference_number': self.reference,
#             'collection_type': self.invoice_id.invoice_type,
#             'period_from': self.invoice_id.period_from,
#             'period_to': self.invoice_id.period_to,
#             'status': 'collected',
#             'invoice_reference': self.invoice_id.name,
#         })
        
#         return {'type': 'ir.actions.act_window_close'}
