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

class SaleOrder(orm.Model):
    """ Model name: Sale Order
    """    
    _inherit = 'sale.order'
    
    # TODO onchange for setup from partner
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(SaleOrder, self).onchange_partner_id(
            cr, uid, ids, part, context=context)
        
        if 'value' not in res:
           res['value'] = {}
        if part:
           partner_proxy = self.pool.get('res.partner').browse(
               cr, uid, part, context=context)
           res['value'][
               'mx_agent_id'] = partner_proxy.agent_id.id
        else:
           res['value']['mx_agent_id'] = False
        return res 
        
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }

class SaleOrderLine(orm.Model):
    """ Model name: Sale Order
    """    
    _inherit = 'sale.order.line'

    # Button event:
    def force_partner_id(self, cr, uid, ids, context=None):
        ''' Force partner from order
        '''
        for line in self.browse(cr, uid, ids, context=None):
            self.write(cr, uid, line.id, {
                'partner_id': line.order_id.partner_id.id,
                }, context=context)
    def force_all_partner_id(self, cr, uid, ids, context=None):
        ''' Force partner from order
        '''
        sol_ids = self.search(cr, uid, [
            ('partner_id', '=', False),
            ], context=context)
        if sol_ids:    
            self.force_partner_id(cr, uid, sol_ids, context=context)
        return True    
        

    def force_agent_id(self, cr, uid, ids, context=None):
        ''' Force agent from order
        '''
        for line in self.browse(cr, uid, ids, context=None):        
            self.write(cr, uid, line.id, {
                'mx_agent_id': line.order_id.mx_agent_id.id or \
                    line.order_id.partner_id.agent_id.id or False,
                }, context=context)
        return True
    def force_all_agent_id(self, cr, uid, ids, context=None):
        ''' Force agent from order
        '''
        sol_ids = self.search(cr, uid, [
            ('mx_agent_id', '=', False),
            ], context=context)
        if sol_ids:    
            self.force_agent_id(cr, uid, sol_ids, context=context)
        return True
    
    def _get_agent_from_order(self, cr, uid, ids, context=None):
        ''' When change sol line order
        '''
        sale_pool = self.pool['sale.order']
        res = []
        for sale in sale_pool.browse(cr, uid, ids, context=context):
            for line in sale.order_line:
                res.append(line.id)
        return res

    def _get_agent_from_sol(self, cr, uid, ids, context=None):
        ''' When change sol line order
        '''
        return ids

    _columns = {
        'mx_agent_id': fields.related(
            'order_id', 'mx_agent_id', type='many2one', relation='res.partner', 
            store={
                'sale.order.line': (_get_agent_from_sol, ['order_id'], 10),
                'sale.order': (_get_agent_from_order, [
                    'partner_id', 'mx_agent_id'], 10),
                }, string='Mx Agent',            
            )
        }#'partner_id', 


class AccountInvoiceRefund(orm.Model):
    """ Model name: Account Invoice Refund
    """    
    _inherit = 'account.invoice.refund'
    
    # Override:
    def compute_refund(self, cr, uid, ids, mode='refund', context=None):
        ''' Add also agent
        '''        
        res = super(AccountInvoiceRefund, self).compute_refund(
            cr, uid, ids, mode=mode, context=context)
            
        # Update agent for refund: 
        if context is None:
            context = {}            
        # Read invoice origin from context
        invoice_pool = self.pool.get('account.invoice')
        active_ids = context.get('active_ids', [])
        for refund in invoice_pool.browse(
                cr, uid, active_ids, context=context):
            invoice_pool.write(cr, uid, refund.id, {
                'mx_agent_id': refund.partner_id.agent_id.id,
                }, context=context)
        return res

class AccountInvoice(orm.Model):
    """ Model name: Account Invoice
    """    
    _inherit = 'account.invoice'
    
    # Override partner_id onchange for set up carrier_id
    def onchange_partner_id(self, cr, uid, ids, type, partner_id, date_invoice, 
            payment_term, partner_bank_id, company_id, context=None):
        ''' Set also carrier ID and default payment
        '''    
        res = super(AccountInvoice, self).onchange_partner_id(
            cr, uid, ids, type, partner_id, date_invoice, 
            payment_term, partner_bank_id, company_id, context=context)
        
        if partner_id:
            partner_pool = self.pool.get('res.partner')
            partner_proxy = partner_pool.browse(
                cr, uid, partner_id, context=context)
            res['value'][
                'mx_agent_id'] = partner_proxy.agent_id.id
        else:
            res['value']['mx_agent_id'] = False
        return res    
    
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }

class StockPicking(orm.Model):
    """ Model name: Stock Picking    
    """    
    _inherit = 'stock.picking'
    
    # TODO onchange for setup from partner
    
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }

class StockDdt(orm.Model):
    """ Model name: Stock DDT
    """    
    _inherit = 'stock.ddt'
    
    # TODO onchange for setup from partner
   
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
