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
from openerp import SUPERUSER_ID #, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'sale.order'

    # Procedure to update
    def force_parameter_for_delivery(self, cr, uid, ids, context=None):
        ''' Compute all not closed order for delivery
        '''
        # Update status:
        _logger.info('Start update close and production')
        self.scheduled_check_close_order(cr, uid, context=context)
        
        # Update readability parameter in line
        _logger.info('Readability parameter')
        sol_pool = self.pool.get('sale.order.line')
        
        # Pricelist order are set to closed:        
        order_ids = self.search(cr, uid, [
            ('state', 'not in', ('cancel', 'sent', 'draft')),
            ('mx_closed', '=', False),
            ], context=context)
        
        for order in self.browse(cr, uid, order_ids, context=context):
            # Order counter:
            order_ml_part = 0.0
            order_ml_tot = 0.0
            order_volume_tot = 0.0
            order_volume_part = 0.0
            
            for line in order.order_line:
                delivery_oc = line.product_uom_qty - line.delivered_qty
                if line.product_uom_maked_sync_qty > line.delivered_qty: 
                    # MRP:
                    delivery_b = \
                        line.product_uom_maked_sync_qty - line.delivered_qty
                    delivery_s = delivery_oc - delivery_b
                else:    
                    # STOCK:
                    delivery_b = 0.0
                    delivery_s = delivery_oc - line.delivered_qty
                
                ml = line.product_id.linear_length or 0.0
                volume = line.product_id.volume or 0.0
                
                delivery_ml_total = delivery_oc * ml
                delivery_ml_partial = delivery_b * ml
                delivery_vol_total = delivery_oc * volume
                delivery_vol_partial = delivery_b * volume
                
                order_ml_tot += delivery_ml_total
                order_ml_part += delivery_ml_partial
                order_volume_tot += delivery_vol_total
                order_volume_part += delivery_vol_partial
                sol_pool.write(cr, uid, line.id, {
                    'delivery_oc': delivery_oc,
                    'delivery_b': delivery_b,
                    'delivery_s': delivery_s,
                    'delivery_ml_total': delivery_ml_total,
                    'delivery_ml_partial': delivery_ml_partial,
                    'delivery_vol_total': delivery_vol_total,
                    'delivery_vol_partial': delivery_vol_partial,
                    }, context=context)

            sol_pool.write(cr, uid, line.id, {
                'delivery_ml_total': order_ml_tot,
                'delivery_ml_partial': order_ml_part,
                'delivery_vol_total': order_volume_tot,
                'delivery_vol_partial': order_volume_part,
                }, context=context)
                
        # Update totale in order
        _logger.info('Total order')
        return

    # -----------------
    # Scheduled events:
    # -----------------
    def scheduled_check_close_order(self, cr, uid, context=None):
        ''' Override original procedure for write all producted
        '''
        # Call original to update closed parameters:
        super(SaleOrder, self).scheduled_check_close_order(
            cr, uid, context=context)
  
        # --------------------------------
        # All closed are produced in view:
        # --------------------------------
        sol_pool = self.pool.get('sale.order.line')
        
        # Pricelist order are set to closed:        
        order_ids = self.search(cr, uid, [
            ('state', 'not in', ('cancel', 'sent', 'draft')),
            ('mx_closed', '=', False),
            ], context=context)

        if not order_ids:
            return True

        _logger.info('Update production in order (# %s)' % len(
            order_ids))
           
        produced_ids = []  

        # 3 states:        
        update_line = {
            'delivered': [],
            'produced': [],
            'partial': [],
            'no': [],            
            }

        for order in self.browse(cr, uid, order_ids, context=context):
            all_produced = True
            for line in order.order_line:
                remain = line.product_uom_qty - line.delivered_qty
                if remain <= 0.0: # all delivered:
                    update_line['delivered'].append(line.id)
                else: # Check type of operation:
                    if line.delivered_qty > line.product_uom_maked_sync_qty: 
                        # ------
                        # stock:
                        # ------
                        if line.product_uom_qty <= line.delivered_qty:
                            update_line['delivered'].append(line.id)
                        else:
                            update_line['partial'].append(line.id)
                            all_produced = False

                    else:
                        # ----
                        # mrp:
                        # ----
                        if line.product_uom_qty <= \
                                line.product_uom_maked_sync_qty:
                            update_line['produced'].append(line.id)
                        elif line.product_uom_maked_sync_qty > \
                                line.delivered_qty:                           
                            update_line['partial'].append(line.id)
                            all_produced = False
                        else: 
                            update_line['no'].append(line.id)
                            all_produced = False

            if all_produced:
                produced_ids.append(order.id)

        closed_state = ('delivered', )
        for key in update_line:
            if update_line[key]:
                data = {
                    'mrp_production_state': key,
                    }
                if key in closed_state:
                    data.update({'mx_closed': True})
                    
                sol_pool.write(
                    cr, uid, update_line[key], data, context=context)
                _logger.info('Line %s delivered (# %s)' % (
                    key,
                    len(update_line[key]),
                    ))
               
        if produced_ids:
            self.write(cr, uid, produced_ids, {
                'all_produced': True,
                }, context=context)                
            _logger.info('Order all produced (# %s)' % len(
                produced_ids))
        return True        
    
    # Button event:
    def to_print(self, cr, uid, ids, context=None):
        header_mod = self.write(cr, uid, ids, {
            'print': True}, context=context)
        return True

    def no_print(self, cr, uid, ids, context = None):
        header_mod = self.write(cr, uid, ids, {
            'print': False}, context=context)
        return True

    _columns = {
        'all_produced': fields.boolean('All produced'),
        'print': fields.boolean('To Print'),

        # Total:
        'delivery_ml_total': fields.float('m/l tot', digits=(16, 2)),             
        'delivery_ml_partial': fields.float('m/l part', digits=(16, 2)),
        'delivery_vol_total': fields.float('vol. tot', digits=(16, 2)),
        'delivery_vol_partial': fields.float('vol. part', digits=(16, 2)),             
        }

class SaleOrderLine(orm.Model):
    """ Model name: SaleOrderLine
    """
    _inherit = 'sale.order.line'

    _columns = {
        'mrp_production_state': fields.selection([
            ('delivered', 'Delivered'),
            ('produced', 'All produced'),
            ('partial', 'Partial deliver'),
            ('no', 'Nothing to deliver'),
            ], 'Production state', readonly=False),
        
        'delivery_oc': fields.float('OC remain', digits=(16, 2)),     
        'delivery_b': fields.float('B(lock)', digits=(16, 2)),     
        'delivery_s': fields.float('S(uspend)', digits=(16, 2)),             
        
        'delivery_ml_total': fields.float('m/l tot', digits=(16, 2)),             
        'delivery_ml_partial': fields.float('m/l part', digits=(16, 2)),
        'delivery_vol_total': fields.float('vol. tot', digits=(16, 2)),             
        'delivery_vol_partial': fields.float('vol. part', digits=(16, 2)),             
        }

    _defaults = {
        'mrp_production_state': lambda *x: 'no',            
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
