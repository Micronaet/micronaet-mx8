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

class ResCompany(orm.Model):
    """ Model name: Res Company
    """
    
    _inherit = 'res.company'
    
    # Utility:
    def get_refund_information(self, cr, uid, company_id=0, context=None):
        ''' Return current company refund paramters        
        '''
        if company_id:
            company_ids = self.search(cr, uid, [
                ('id', '=', company_id)], context=context)
        else:    
            company_ids = self.search(cr, uid, [], context=context)
        return self.browse(cr, uid, company_ids, context=context)[0]
        
    _columns = {
        'refund_account_id': fields.many2one(
            'account.account', 'Refund account'),     
        'refund_product_id': fields.many2one(
            'product.product', 'Product'),
        'refund_cost': fields.float('Refund cost', 
            help='Number of effects to pay',
            digits=(16, 2)),                    
        }

class AccountPaymentTerm(orm.Model):
    """ Model name: AccountPaymentTerm
    """    
    _inherit = 'account.payment.term'
    
    _columns = {
        'has_refund': fields.boolean('has refund cost'),
        'refund_number': fields.float('# effects', 
            help='Number of effects to pay',
            digits=(16, 2)), 
        }

class AccountInvoice(orm.Model):
    """ Model name: AccountInvoice
    """    
    _inherit = 'account.invoice'
    
    def create_update_refund(self, cr, uid, invoice_proxy, context=None):
        ''' Function called by create and update procedure.
            Generate line with refund value        
        '''
        # ---------------------------------------------------------------------
        #                        Read parameters:
        # ---------------------------------------------------------------------
        # Company:
        company_param = self.pool.get('res.company').get_refund_information(
                cr, uid, context=context)
        refund_account_id = company_param.refund_account_id
        refund_product_id = company_param.refund_product_id
        price_unit = company_param.refund_cost
        
        # Payment:
        refund_number = invoice_proxy.payment_term.refund_number or 1

        # Related:
        product_id = refund_product_id.id
        uos_id = refund_product_id.uom_id.id # XXX UOM
        name = refund_product_id.name
        
        # Calculated:
        quantity = refund_number * price_unit
        
        # ---------------------------------------------------------------------
        #                      Update create refund line:
        # ---------------------------------------------------------------------
        res_id = invoice_proxy.id
        refund = invoice_proxy.payment_term # readability
        line_pool = self.pool.get('account.invoice.line')
        line_ids = line_pool.search(cr, uid, [
            ('invoice_id', '=', res_id),
            ('refund_line', '=', True),
            ], context=context)

        # On change function:
        data = line_pool.product_id_change(cr, uid, False, product_id,
            uos_id, quantity, name, invoice_proxy.type, 
            invoice_proxy.partner_id.id, invoice_proxy.fiscal_position.id, 
            price_unit, invoice_proxy.currency_id.id, 
            invoice_proxy.company_id.id, context=context).get('value', {})
        
        if 'invoice_line_tax_id' in data:
            data['invoice_line_tax_id'] = [(6, 0, data['invoice_line_tax_id'])]
        
        data.update({
            'account_id': refund_account_id.id,
            'sequence': 100000,
            'invoice_id': res_id,
            'price_unit': price_unit,
            'uos_id': uos_id,
            'discount': 0.0,
            'product_id': product_id,
            'quantity': quantity,
            'name': name,
            'refund_line': True
            })
            
        if line_ids:
            if len(line_ids) > 1:
                _logger.error('More than one refund line: %s' % res_id)
            line_pool.write(cr, uid, line_ids[0], data, context=context)
        else:
            line_pool.create(cr, uid, data, context=context)
        return True    
        
    # Override function to create
    def create(self, cr, uid, vals, context=None):
        """ Create a new record for a model AccountInvoice
            @param cr: cursor to database
            @param uid: id of current user
            @param vals: provides a data for new record
            @param context: context arguments, like lang, time zone
            
            @return: returns a id of new record
        """
    
        res_id = super(AccountInvoice, self).create(
            cr, uid, vals, context=context)
            
        # Check refund line:
        invoice_proxy = self.browse(cr, uid, res_id, context=context)
        if not invoice_proxy.payment_term.has_refund:
            return res_id
            
        self.create_update_refund(cr, uid, invoice_proxy, context=context)            
        return res_id
        
    ''' TODO write also for modiication in payment!!
    def write(self, cr, uid, ids, vals, context=None):
        """ Update redord(s) comes in {ids}, with new value comes as {vals}
            return True on success, False otherwise
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of record ids to be update
            @param vals: dict of new values to be set
            @param context: context arguments, like lang, time zone
            
            @return: True on success, False otherwise
        """
    
        #TODO: process before updating resource
        res = super(AccountInvoice, self).write(
            cr, uid, ids, vals, context=context)
        return res'''
    

class AccountInvoiceLine(orm.Model):
    """ Model name: AccountInvoiceLine
    """
    
    _inherit = 'account.invoice.line'

    _columns = {
        'refund_line': fields.boolean('Refund line', 
            help='Used for check the creation or the presence'),
        }
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
