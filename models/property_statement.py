# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class PropertyStatement(models.Model):
    _name = 'property.statement'
    _description = 'Customer Statement of Account'
    _order = 'transaction_date desc'
    _rec_name = 'reference'

    tenant_id = fields.Many2one('property.tenant', string='Tenant', required=True, ondelete='cascade')
    transaction_date = fields.Date(string='Transaction Date', required=True, default=fields.Date.context_today)
    reference = fields.Char(string='Reference', required=True)
    description = fields.Text(string='Description')
    transaction_type = fields.Selection([
        ('rent', 'Rent Payment'),
        ('deposit', 'Security Deposit'),
        ('parking', 'Parking Charges'),
        ('other_charges', 'Other Charges'),
        ('refund', 'Refund'),
        ('penalty', 'Penalty'),
        ('adjustment', 'Adjustment'),
    ], string='Transaction Type', required=True)
    
    debit_amount = fields.Float(string='Debit Amount', digits=(16, 2), default=0.0)
    credit_amount = fields.Float(string='Credit Amount', digits=(16, 2), default=0.0)
    running_balance = fields.Float(string='Running Balance', digits=(16, 2), compute='_compute_running_balance', store=True)
    
    room_id = fields.Many2one('property.room', string='Room')
    agreement_id = fields.Many2one('property.agreement', string='Agreement')
    collection_id = fields.Many2one('property.collection', string='Collection')
    
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    @api.depends('tenant_id', 'transaction_date', 'debit_amount', 'credit_amount')
    def _compute_running_balance(self):
        for record in self:
            # Get all previous transactions for this tenant
            previous_transactions = self.search([
                ('tenant_id', '=', record.tenant_id.id),
                ('transaction_date', '<=', record.transaction_date),
                ('id', '<=', record.id)
            ], order='transaction_date asc, id asc')
            
            balance = 0.0
            for transaction in previous_transactions:
                balance += transaction.debit_amount - transaction.credit_amount
            
            record.running_balance = balance

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.reference} - {record.tenant_id.name}"
            result.append((record.id, name))
        return result

    @api.model
    def create_from_collection(self, collection):
        """Create statement entry from collection record"""
        description = f"Payment for {collection.collection_type}"
        if collection.room_id:
            description += f" - Room {collection.room_id.name}"
        
        transaction_type = 'rent'
        if collection.collection_type == 'deposit':
            transaction_type = 'deposit'
        elif collection.collection_type == 'parking':
            transaction_type = 'parking'
        elif collection.collection_type == 'other':
            transaction_type = 'other_charges'
        
        vals = {
            'tenant_id': collection.tenant_id.id,
            'transaction_date': collection.date,
            'reference': collection.receipt_number or f"COL/{collection.id}",
            'description': description,
            'transaction_type': transaction_type,
            'credit_amount': collection.amount_collected,
            'debit_amount': 0.0,
            'room_id': collection.room_id.id if collection.room_id else False,
            'agreement_id': collection.agreement_id.id if collection.agreement_id else False,
            'collection_id': collection.id,
        }
        
        return self.create(vals)

    @api.model
    def create_from_agreement(self, agreement):
        """Create statement entries from agreement charges"""
        statements = self.env['property.statement']
        
        # Security deposit entry
        if agreement.deposit_amount > 0:
            vals = {
                'tenant_id': agreement.tenant_id.id,
                'transaction_date': agreement.start_date,
                'reference': f"AGR/{agreement.id}/DEPOSIT",
                'description': f"Security deposit for agreement {agreement.name}",
                'transaction_type': 'deposit',
                'debit_amount': agreement.deposit_amount,
                'credit_amount': 0.0,
                'room_id': agreement.room_id.id,
                'agreement_id': agreement.id,
            }
            statements += self.create(vals)
        
        # Monthly rent entries
        current_date = agreement.start_date
        while current_date <= agreement.end_date:
            vals = {
                'tenant_id': agreement.tenant_id.id,
                'transaction_date': current_date,
                'reference': f"AGR/{agreement.id}/RENT/{current_date.strftime('%Y%m')}",
                'description': f"Monthly rent for {current_date.strftime('%B %Y')}",
                'transaction_type': 'rent',
                'debit_amount': agreement.rent_amount,
                'credit_amount': 0.0,
                'room_id': agreement.room_id.id,
                'agreement_id': agreement.id,
            }
            statements += self.create(vals)
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return statements


class PropertyTenant(models.Model):
    _inherit = 'property.tenant'

    statement_ids = fields.One2many('property.statement', 'tenant_id', string='Statement of Account')
    statement_count = fields.Integer(string='Statement Entries', compute='_compute_statement_count')
    total_debits = fields.Float(string='Total Debits', compute='_compute_statement_totals')
    total_credits = fields.Float(string='Total Credits', compute='_compute_statement_totals')
    current_balance = fields.Float(string='Current Balance', compute='_compute_statement_totals')

    @api.depends('statement_ids')
    def _compute_statement_count(self):
        for tenant in self:
            tenant.statement_count = len(tenant.statement_ids)

    @api.depends('statement_ids.debit_amount', 'statement_ids.credit_amount')
    def _compute_statement_totals(self):
        for tenant in self:
            tenant.total_debits = sum(tenant.statement_ids.mapped('debit_amount'))
            tenant.total_credits = sum(tenant.statement_ids.mapped('credit_amount'))
            tenant.current_balance = tenant.total_debits - tenant.total_credits

    def action_view_statement(self):
        """Action to view tenant's statement of account"""
        self.ensure_one()
        return {
            'name': f'Statement of Account - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'property.statement',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {
                'default_tenant_id': self.id,
                'search_default_tenant_id': self.id,
            },
            'target': 'current',
        }

    def action_generate_statement_report(self):
        """Generate statement report for specific period"""
        return {
            'name': 'Generate Statement Report',
            'type': 'ir.actions.act_window',
            'res_model': 'property.statement.wizard',
            'view_mode': 'form',
            'context': {
                'default_tenant_id': self.id,
            },
            'target': 'new',
        }


class PropertyCollection(models.Model):
    _inherit = 'property.collection'

    statement_id = fields.Many2one('property.statement', string='Statement Entry', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        collections = super().create(vals_list)
        for collection in collections:
            if collection.tenant_id and collection.status == 'confirmed':
                statement = self.env['property.statement'].create_from_collection(collection)
                collection.statement_id = statement.id
        return collections

    def write(self, vals):
        result = super().write(vals)
        for collection in self:
            if 'status' in vals and vals['status'] == 'confirmed' and collection.tenant_id and not collection.statement_id:
                statement = self.env['property.statement'].create_from_collection(collection)
                collection.statement_id = statement.id
        return result


class PropertyAgreement(models.Model):
    _inherit = 'property.agreement'

    statement_ids = fields.One2many('property.statement', 'agreement_id', string='Statement Entries')

    def action_generate_statement_entries(self):
        """Generate statement entries for this agreement"""
        self.ensure_one()
        if not self.statement_ids:
            statements = self.env['property.statement'].create_from_agreement(self)
            return {
                'name': 'Statement Entries Generated',
                'type': 'ir.actions.act_window',
                'res_model': 'property.statement',
                'view_mode': 'list',
                'domain': [('id', 'in', statements.ids)],
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Statement entries already exist for this agreement.',
                    'type': 'warning',
                }
            }