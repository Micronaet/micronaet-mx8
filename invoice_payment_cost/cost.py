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

class AccountPaymentTerm(orm.Model):
    """ Model name: AccountPaymentTerm
    """
    
    _inherit = 'account.payment.term'
    
    _columns = {
        'has_refund': fields.boolean('has refund cost'),
        'refund_cost': fields.float('Refund cost', 
            digits=(16, 2)), 
        'refund_account_id': fields.many2one(
            'account.account', 'Refund account'),     
        'refund_product_id': fields.many2one(
            'product.product', 'Product'),     
        }

class AccountInvoice(orm.Model):
    """ Model name: AccountInvoice
    """
    
    _inherit = 'account.invoice'
    
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
        import pdb; pdb.set_trace()
        # Generate line with refund value:
        refund = invoice_proxy.payment_term # readability
        line_pool = self.pool.get('account.invoice.line')
        line_ids = line_pool.search(cr, uid, [
            ('invoice_id', '=', res_id),
            ('refund_line', '=', True),
            ], context=context)
            
        data = {
            'account_id': refund.refund_account_id.id,
            'sequence': 100000,
            'invoice_id': res_id,
            'price_unit': refund.refund_cost,
            'uos_id': refund.refund_product_id.uom_id.id,
            'discount': 0.0,
            'product_id': refund.refund_product_id.id,
            'quantity': refund.refund_cost,
            'name': refund.refund_product_id.name,
            'refund_line': True
            }
            
        if line_ids:
            line_pool.write(cr, uid, line_ids[0], data, context=context)
        else:
            line_pool.create(cr, uid, data, context=context)
            
        return res_id
    

class AccountInvoiceLine(orm.Model):
    """ Model name: AccountInvoiceLine
    """
    
    _inherit = 'account.invoice.line'

    _columns = {
        'refund_line': fields.boolean('Refund line', 
            help='Used for check the creation or the presence'),
        }
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
