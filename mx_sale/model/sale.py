# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    Original module for stock.move from:
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _inherit = 'product.product'

    # Override sale_stock procurement procedure!
    def need_procurement(self, cr, uid, ids, context=None):
        return False

class StockPicking(orm.Model):
    ''' Add alternative method for picking creation
    '''
    _inherit = 'stock.picking'
    
    """def force_assign_pick_to_ddt(self, cr, uid, ids, context=None):
        ''' Force creation of new DDT using wizard and associate
        '''
        wizard_pool = self.pool.get('ddt.from.pickings')
        context['active_ids'] = ids 
        wizard_id = wizard_pool.create(cr, uid, {}, context=context)
            
        wizard_pool.create(cr, uid, [wizard_id], context=context)
        return True"""
    
    def open_ddt_report(self, cr, uid, ids, context=None):
        ''' Open DDT form if present        
        '''
        return True
        
    def open_ddt_form(self, cr, uid, ids, context=None):
        ''' Open DDT report directly if present
        '''
        return True
    
    
    _columns = {
        'sale_id': fields.many2one('sale.order', 'Sale order'), 
        }

class ResPartner(orm.Model):
    ''' Extra field for partner
    '''    
    _inherit = 'res.partner'
    
    _columns = {
        'incoterm_id':fields.many2one(
            'stock.incoterms', 'Default incoterm', ondelete='set null'),        
        }

class SaleOrder(orm.Model):
    ''' Extra field for order
    '''    
    _inherit = 'sale.order'    
    
    # -------------------------------------------------------------------------
    #                                  Button events:
    # -------------------------------------------------------------------------
    def button_force_all_deadline_date(self, cr, uid, ids, context=None):
        ''' Force sale order date on all lines
        '''
        order_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        line_ids = [line.id for line in order_proxy.order_line]
        self.pool.get('sale.order.line').write(cr, uid, line_ids, {
            'date_deadline': order_proxy.date_deadline,
            }, context=context)
            
        return True

    # -------------------------------------------------------------------------
    #                                  Override:
    # -------------------------------------------------------------------------
    # onchange:
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        ''' Override standard procedure for add extra account field:        
        '''
        # Call original procedure:
        res = super(SaleOrder, self).onchange_partner_id(
            cr, uid, ids, partner_id, context=context)
        if 'value' not in res:
            res['value'] = {}
        
        # Append extra value:
        if not partner_id: # reset:
            res['value'].update({
                'incoterm': False,                
                'carrier_id': False,
                'carriage_condition_id': False,
                'goods_description_id': False,
                'transportation_reason_id': False,
                'payment_term_id': False,
                'bank_account_id': False,
                })
            return res

        partner_pool = self.pool.get('res.partner')
        partner_proxy = partner_pool.browse(cr, uid, partner_id, 
            context=context)
        
        res['value'].update({
            'incoterm': partner_proxy.incoterm_id.id,
            'carrier_id': partner_proxy.default_carrier_id.id,
            'carriage_condition_id': partner_proxy.carriage_condition_id.id,
            'goods_description_id': partner_proxy.goods_description_id.id,
            'transportation_reason_id': 
                partner_proxy.transportation_reason_id.id,
            'payment_term_id': partner_proxy.property_payment_term.id,            
            })
        # Set default account for partner    
        if partner_proxy.bank_ids:
            res['value']['bank_account_id'] = partner_proxy.bank_ids[0].id
            
        return res

    _columns = {
        # QUOTATION:
        'date_valid': fields.date('Validity date', 
            help='Max date for validity of offer'),
        
        # ORDER:
        'date_confirm': fields.date('Date confirm', 
            help='Order confirm by the customer'), # TODO yet present in order?
        'date_deadline': fields.date('Order deadline', 
            help='Delivery term for customer'),
        # Fixed by delivery team:
        'date_booked': fields.date('Booked date', 
            help='Delivery was booked and fixed!'),            
        'date_booked_confirmed': fields.boolean('Booked confirmed',
            help='Booked confirmed for this date'),
        'date_delivery': fields.date('Load / Availability',
            help='For ex works is availability date, other clause is '
                'load date'),
        'date_delivery_confirmed': fields.boolean('Delivery confirmed',
            help='Delivery confirmed, product available '
                '(2 cases depend on incoterms)'),
        # TODO used?    
        #'date_previous_deadline': fields.date(
        #    'Previous deadline', 
        #    help="If during sync deadline is modified this field contain old "
        #        "value before update"),         
        # TODO remove:
        # Replaced with date_booked!!!    
        #'date_delivery': fields.date('Delivery', 
        #    help='Contain delivery date, when present production plan work '
        #        'with this instead of deadline value, if forced production '
        #        'cannot be moved'),

        # Account extra field saved in sale.order:
        'default_carrier_id': fields.many2one('delivery.carrier', 'Carrier', 
            domain=[('is_vector', '=', True)]),
        'carriage_condition_id': fields.many2one(
            'stock.picking.carriage_condition', 'Carriage condition'),
        'goods_description_id': fields.many2one(
            'stock.picking.goods_description', 'Goods description'),
        'transportation_reason_id': fields.many2one(
            'stock.picking.transportation_reason', 'Transportation reason'),
        'payment_term_id': fields.many2one(
            'account.payment.term', 'Payment term'),            
        'bank_account_id': fields.many2one(
            'res.partner.bank', 'Partner bank account'),
        'bank_account_company_id': fields.many2one(
            'res.partner.bank', 'Company bank account'),
        
        # Alert:
        'uncovered_payment': fields.boolean('Uncovered payment'),    
        'uncovered_alert': fields.char('Alert', size=64, readonly=True), 

        # TODO not used picking_ids!!!        
        'stock_picking_ids': fields.one2many(
            'stock.picking', 'sale_id', 'Delivery'),        
        }
        
    _defaults = {
        'uncovered_alert': lambda *x: 'Alert: Uncovered payment!!!',
        'date_valid': lambda *x: (
            datetime.now() + timedelta(days=15)).strftime(
                DEFAULT_SERVER_DATE_FORMAT),
        }   
     

class SaleOrderLine(orm.Model):
    ''' Extra field for order line
    '''    
    _inherit = 'sale.order.line'
    
    # ----------------
    # Function fields:
    # ----------------
    def _function_get_delivered(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate delivered elements in picking orders
        '''
        res = {}
        move_pool = self.pool.get('stock.move')
        
        for line in self.browse(cr, uid, ids, context=context):            
            res[line.id] = 0.0
            move_ids = move_pool.search(cr, uid, [
                ('sale_line_id', '=', line.id)], context=context)                
            for move in move_pool.browse(cr, uid, move_ids, context=context):
                # TODO jump picking for virtual count!!!!!!!!!!!!!!!!!!!!!!!!!!
                #if move.picking_id.ddt_number: # was marked as DDT
                # TODO check UOM!!! for 
                res[line.id] += move.product_qty
        return res
        
    _columns = {
        'gr_weight': fields.float('Gross weight'),
        'colls': fields.integer('Colls'), 
        #states={'draft': [('readonly', False)]}),
        
        'date_deadline': fields.date('Deadline'),
        'date_delivery': fields.related( # TODO use booked!!!!
            'order_id', 'date_delivery', type='date', string='Date delivery'),
            
        'alias_id':fields.many2one(
            'product.product', 'Marked as product', ondelete='set null'),

        'delivered_qty': fields.function(
            _function_get_delivered, method=True, type='float', readonly=True,
            string='Delivered', store=False, 
            help='Quantity delivered with DDT out'),            
        }
    _defaults = {
        'colls': lambda *x: 1,
        }    

class StockMove(orm.Model):
    ''' Extra field for order line
    '''    
    _inherit = 'stock.move'
        
    _columns = {
        'sale_line_id': fields.many2one('sale.order.line', 'Sale line'), 
        }    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
