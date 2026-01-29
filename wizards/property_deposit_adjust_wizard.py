# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PropertyDepositAdjustWizard(models.TransientModel):
    _name = 'property.deposit.adjust.wizard'
    _description = 'Adjust Deposit against Rent'

    agreement_id = fields.Many2one('property.agreement', 'Agreement', required=True)
    tenant_id = fields.Many2one(related='agreement_id.tenant_id', readonly=True)
    
    # Financials
    rent_outstanding = fields.Monetary('Rent Outstanding', currency_field='currency_id', compute='_compute_outstanding')
    deposit_held = fields.Monetary('Deposit Amount', currency_field='currency_id', compute='_compute_outstanding', help="Total Security Deposit Amount from Agreement")
    
    amount = fields.Monetary('Adjustment Amount', required=True, currency_field='currency_id')
    date = fields.Date('Date', default=fields.Date.today, required=True)
    description = fields.Char('Description', default='Adjusting deposit against rent due')
    
    currency_id = fields.Many2one(related='agreement_id.currency_id')
    
    @api.depends('agreement_id')
    def _compute_outstanding(self):
        for rec in self:
            if rec.agreement_id:
                # Calculate Rent Outstanding based on Statement Entries
                # Filter for Rent-related transactions
                stmts = self.env['property.statement'].search([
                    ('agreement_id', '=', rec.agreement_id.id),
                    ('transaction_type', '=', 'rent')
                ])
                rec.rent_outstanding = sum(stmts.mapped('debit_amount')) - sum(stmts.mapped('credit_amount'))
                
                # Use agreement deposit amount as reference
                rec.deposit_held = rec.agreement_id.deposit_amount
            else:
                rec.rent_outstanding = 0
                rec.deposit_held = 0

    def action_confirm(self):
        self.ensure_one()
        
        # Create Collection (Auto-verified)
        # This will trigger the logic handling 'deposit_adjustment' payment method
        collection = self.env['property.collection'].create({
            'date': self.date,
            'amount_collected': self.amount,
            'tenant_id': self.tenant_id.id,
            'room_id': self.agreement_id.room_id.id,
            'agreement_id': self.agreement_id.id,
            'collection_type': 'rent', # We are paying off Rent
            'payment_method': 'deposit_adjustment', # Special method triggering debit entry
            'notes': self.description,
            'status': 'verified', # Auto-verify to create statements immediately
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Deposit adjusted successfully! Statement entries created.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
