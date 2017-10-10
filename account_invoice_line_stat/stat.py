# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)

class AccountInvoiceLine(orm.Model):
    """ Model name: Account invoice line
    """    
    _inherit = 'account.invoice.line'
    
    """def _get_date_order_from_order(self, cr, uid, ids, context=None):
        ''' When change sol line order
        '''
        sale_pool = self.pool['sale.order']
        res = []
        for sale in sale_pool.browse(cr, uid, ids, context=context):
            for line in sale.order_line:
                res.append(line.id)
        return res

    def _get_date_order_from_sol(self, cr, uid, ids, context=None):
        ''' When change sol line order
        '''
        return ids

    def _get_default_code_from_sol(self, cr, uid, ids, context=None):
        ''' When change sol line order
        '''
        return ids

        'default_code': fields.related(
            'product_id', 'default_code', type='char',
            store={
                'sale.order.line': (
                    _get_default_code_from_sol, ['product_id'], 10),
                }, string='Default code', 
            ),
        'order_date': fields.related(
            'order_id', 'date_order', type='date',
            store={
                'sale.order.line': (_get_date_order_from_sol, ['order_id'], 10),
                'sale.order': (_get_date_order_from_order, [
                    'date_order'], 10),
                }, string='Order date',            
            )
    """
    # Temporary procedure:
    def first_populate_date_invoice(self, cr, uid, context=None):
        ''' First populate of date taked from account invoice
        '''
        invoice_pool = self.pool.get('account.invoice')
        invoice_ids = invoice_pool.search(cr, uid, [
            #('type', '=', 'out_invoice'),
            ], context=context)
        res = []
        _logger.info('To update invoice: %s' % len(invoice_ids)) 

        i = 0

        for invoice in invoice_pool.browse(
                cr, uid, invoice_ids, context=context):                
            i += 1            
            if i % 100 == 0:
                _logger.info('... reading invoice: %s' % i)
            if invoice.date_invoice: # only invoice with date!
                res.append((invoice.id, invoice.date_invoice))
            
        i = 0
        for invoice_id, date_invoice in res:
            i += 1
            if i % 100 == 0:
                _logger.info('... updating invoice: %s' % i)
            invoice_pool.write(cr, uid, invoice_id, {
                'date_invoice': date_invoice,
                }, context=context)
            # Will be updated     
        return True    
        
    def _get_first_supplier_from_product(self, cr, uid, ids, context=None):
        ''' When change first supplier in product
        '''
        line_pool = self.pool.get('account.invoice.line')
        _logger.info('Update account line (change first supplier product)')
        return line_pool.search(cr, uid, [
            ('product_id', 'in', ids)], context=context)
            
    def _get_first_supplier_from_product_line(
            self, cr, uid, ids, context=None):
        ''' When change product_id in sol line order 
        '''
        _logger.info('Update account line (change product in line) %s' % (  
            len(ids)))
        return ids

    def _get_invoice_destination(self, cr, uid, ids, context=None):
        ''' When change sol line order
        '''
        line_pool = self.pool.get('account.invoice.line')
        #_logger.info('Update account line (change invoice destination)')
        return line_pool.search(cr, uid, [
            ('invoice_id', 'in', ids)], context=context)

    def _get_invoice_agent(self, cr, uid, ids, context=None):
        ''' When change invoice agent
        '''
        line_pool = self.pool.get('account.invoice.line')
        #_logger.info('Update account line (change agent in invoice)')
        return line_pool.search(cr, uid, [
            ('invoice_id', 'in', ids)], context=context)

    def _get_invoice_date_change(self, cr, uid, ids, context=None):
        ''' When change invoice date 
        '''
        line_pool = self.pool.get('account.invoice.line')
        #_logger.info('Update account line (change date invoice)')
        return line_pool.search(cr, uid, [
            ('invoice_id', 'in', ids)], context=context)

    # -------------------------------------------------------------------------
    # Store function region_id:
    # -------------------------------------------------------------------------
    def _refresh_invoice_partner(self, cr, uid, ids, context=None):
        ''' Change account.invoice >> partner_id
        '''
        line_ids = self.pool.get('account.invoice.line').search(cr, uid, [
            ('invoice_id', 'in', ids),
            ], context=context)
        _logger.warning('Line of invoice change partner: %s' % len(line_ids))
        
        return line_ids

    def _refresh_res_partner_city(self, cr, uid, ids, context=None):
        ''' Change res.partner >> state_id
        '''
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [
            ('partner_id', 'in', ids),
            ], context=context)            
        _logger.warning(
            'Invoice of partner change state: %s' % len(invoice_ids))    
        
        return self.pool.get('account.invoice.line')._refresh_invoice_partner(
            cr, uid, invoice_ids, context=context)

    def _refresh_state_region(self, cr, uid, ids, context=None):
        ''' Change res.country.state >> region_id
        '''
        partner_ids = self.pool.get('res.partner').search(cr, uid, [
            ('state_id', 'in', ids),
            ], context=context)
        _logger.warning('Partner of city change region: %s' % len(partner_ids))    
        
        return self.pool.get('account.invoice.line')._refresh_res_partner_city(
            cr, uid, partner_ids, context=context)
    
    
    # -------------------------------------------------------------------------
    # Store function state_id:
    # -------------------------------------------------------------------------
    def _refresh_state_id_invoice_partner_id(self, cr, uid, ids, context=None):
        ''' Change partner_id (account.invoice)
        '''
        return self.pool.get('account.invoice.line').search(cr, uid, [
            ('invoice_id', 'in', ids), # line with this invoice partner changed
            ], context=context)

    def _refresh_state_id_partner_state_id(self, cr, uid, ids, context=None):
        ''' Change partner state (res.partner)
        '''
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [
           ('partner_id', 'in', ids),
           ], context=context)
        return self.pool.get('account.invoice.line'
            )._refresh_state_id_invoice_partner_id(
                cr, uid, invoice_ids, context=context)
    
    # -------------------------------------------------------------------------
    # Field function:
    # -------------------------------------------------------------------------
    def _get_line_state_id(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''       
        res = {}     
        for line in self.browse(cr, uid, ids, context=context):
            try:
                res[line.id] = line.invoice_id.partner_id.state_id.id
            except:
                res[line.id] = False                    
        return res
        
    def _get_region_invoiced_line(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''       
        res = {}     
        for line in self.browse(cr, uid, ids, context=context):
            try:
                res[line.id] = line.invoice_id.partner_id.state_id.region_id.id
            except:
                res[line.id] = False                    
        return res

    _columns = {
        'date_invoice': fields.related(
            'invoice_id', 'date_invoice', 
            type='date', string='Date', store={
                'account.invoice': (
                    _get_invoice_date_change, ['date_invoice'], 10),    
                }),             

        'region_id': fields.function(
            _get_region_invoiced_line, method=True, 
            type='many2one', string='Regione', relation='res.country.region',
            store={
                'account.invoice': (
                    _refresh_invoice_partner, ['partner_id'], 10),
                'res.partner': (
                    _refresh_res_partner_city, ['state_id'], 10),
                'res.country.state': (
                    _refresh_state_region, ['region_id'], 10),
                }), 

        'state_id': fields.function(
            _get_line_state_id, method=True, 
            type='many2one', string='Città', relation='res.country.state',
            store={
                'account.invoice': (
                    _refresh_state_id_invoice_partner_id, ['partner_id'], 10),
                'res.partner': (
                    _refresh_state_id_partner_state_id, ['state_id'], 10),
                }), 

        # TODO change:
        'country_id': fields.related(
            'partner_id', 'country_id', 
            type='many2one', relation='res.country', 
            string='Country', store=True),

        'destination_partner_id': fields.related(
            'invoice_id', 'destination_partner_id', 
            type='many2one', string='Destination', relation='res.partner',
            store={
                'account.invoice': (_get_invoice_destination, [
                    'destination_partner_id'], 10),    
                }),

        'mx_agent_id': fields.related(
            'invoice_id', 'mx_agent_id', 
            type='many2one', string='Agent', relation='res.partner',
            store={
                'account.invoice': (_get_invoice_agent, [
                    'mx_agent_id'], 10),    
                # TODO force also in partner change agent    
                }),

        'first_supplier_id': fields.related(
            'product_id', 'first_supplier_id', 
            type='many2one', string='First supplier', relation='res.partner',
            store={
                'product.product': (_get_first_supplier_from_product, [
                    'first_supplier_id'], 10),
                'account.invoice.line': (_get_first_supplier_from_product_line,
                    ['product_id'], 10),
                 # TODO add product_id                    
                }),
        
        'type': fields.related(
            'invoice_id', 'type', 
            type='selection', selection=[
                ('out_invoice', 'Customer Invoice'),
                ('in_invoice', 'Supplier Invoice'),
                ('out_refund', 'Customer Refund'),
                ('in_refund', 'Supplier Refund'),
                ], string='Type', store=True),
                
        'zone_id': fields.related(
            'partner_id', 'zone_id', 
            type='many2one', relation='res.partner.zone', 
            string='Zone', store=True),

        #'property_account_position': fields.related(
        #    'partner_id', 'property_account_position', 
        #    type='many2one', relation='account.fiscal.position', 
        #    string='Fiscal position', store=True),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
