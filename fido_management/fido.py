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

# TODO move in a module:
# TODO REMOVE !!!!
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
class SaleOrder(orm.Model):
    ''' FIDO in order 
    '''
    _inherit ='sale.order'
    
    def _get_open_amount_total_order(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = 0.0
            for line in order.order_line:
                remain = line.product_uom_qty - line.delivered_qty
                if remain and line.product_uom_qty:
                    res[order.id] += \
                        line.price_subtotal * remain / line.product_uom_qty
        return res

    _columns = {
        'open_amount_total': fields.function(
            _get_open_amount_total_order, method=True, 
            type='float', string='Open amount', 
            store=False),                         
        }
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

class StockPicking(orm.Model):
    ''' FIDO in ddt 
    '''
    _inherit ='stock.picking'
    
    def _get_open_amount_total_ddt(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for ddt in self.browse(cr, uid, ids, context=context):
            res[ddt.id] = 0.0
            for line in ddt.move_lines:
                qty = line.product_uom_qty
                
                if qty:
                    # Proportional with subtotal referred in order line:
                    if line.sale_line_id.product_uom_qty:
                        res[ddt.id] += \
                            line.sale_line_id.price_subtotal * qty / \
                                line.sale_line_id.product_uom_qty
                    else:
                        _logger.info('Division by zero!!')            
        return res
        
    _columns = {
        'open_amount_total': fields.function(
            _get_open_amount_total_ddt, method=True, 
            type='float', string='Open amount', 
            store=False),                         
        }

class ResPartner(orm.Model):
    ''' FIDO fields for add management
    '''
    _inherit ='res.partner'
    
    def _get_uncovered_amount_total(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        fido_yellow = 0.85 # TODO parametrize?
        
        for partner in self.browse(cr, uid, ids, context=context):       
            res[partner.id] = {}
            #    'uncovered_amount': 0, 'uncovered_state': 'red'}
            #continue 
            opened = 0.0
            res[partner.id]['uncovered_state'] = 'green'
            
            fido_date = partner.fido_date or False
            fido_total = partner.fido_total or 0.0

            # ---------------------------
            # Payment in date not closed:
            # ---------------------------
            for payment in partner.open_payment_ids:
                invoice_date = payment.invoice_date or payment.deadline or False
                if not fido_date or not invoice_date or \
                        fido_date <= invoice_date:
                    opened += payment.__getattribute__('in')
            
            # ----------
            # OC opened:
            # ----------
            for order in partner.open_order_ids:
                opened += order.open_amount_total
                
            # ----------------
            # DDT not invoice:
            # ----------------
            for ddt in partner.open_picking_ids:
                opened += ddt.open_amount_total
                

            res[partner.id]['uncovered_amount'] = fido_total - opened

            # Check black listed:
            if partner.fido_ko:
                # No computation partner is black listed!
                res[partner.id]['uncovered_state'] = 'black'
                continue

            if not fido_total:
                # No computation no Fido amount!
                res[partner.id]['uncovered_state'] = 'red'
                continue

            if fido_total < opened:
                res[partner.id]['uncovered_state'] = 'red'
            elif opened / fido_total > fido_yellow:
                res[partner.id]['uncovered_state'] = 'yellow'
                
        return res
        
    _columns = {
        'empty': fields.char(' '),
        'fido_date': fields.date('FIDO from date'),
        'fido_ko': fields.boolean('FIDO removed'),
        'fido_total': fields.float('Total FIDO', digits=(16, 2)),
        
        # Open order:
        'open_order_ids': fields.one2many(
            'sale.order', 'partner_id', 
            'Order open', domain=[
                ('mx_closed', '=', False),
                ('pricelist_order', '=', False),
                ('state', 'not in', ('cancel', 'draft', 'sent')),
                ]), 
            
        # Open order:
        'open_picking_ids': fields.one2many(
            'stock.picking', 'partner_id', 
            'Open DDT', domain=[
                ('ddt_id', '!=', False), 
                ('invoice_id', '=', False),
                ]),

        'uncovered_amount': fields.function(
            _get_uncovered_amount_total, method=True, 
            type='float', string='Uncovered amount', 
            store=False, multi=True),
        'uncovered_state': fields.function(
            _get_uncovered_amount_total, method=True, 
            type='selection', string='Uncovered state', 
            store=False, multi=True, selection=[
                ('green', 'OK FIDO'),
                ('yellow', '> 85% FIDO'),
                ('red', 'FIDO uncovered or no FIDO'),
                ('black', 'FIDO removed'),
                ]),
        }
    _defaults = {
        'empty': lambda *x: ' ',
        }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
