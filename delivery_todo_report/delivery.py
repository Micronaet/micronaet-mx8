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

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """
    
    _inherit = 'res.partner'
    
    _columns = {
        'extra_description_load_list': fields.boolean('Descrizione extra',
            help='Attiva la colonna extra descrizione nella lista di carico'),
        }

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'sale.order'

    def open_detailed_order(self, cr, uid, ids, context=None):
        ''' Open detailed order popup
        '''
        # Choose form:
        try:        
            model_pool = self.pool.get('ir.model.data')
            form_view = model_pool.get_object_reference(
                cr, uid, 'delivery_todo_report', 
                'view_sale_order_delivery_form')[1]
        except:
            tree_view = False        

        return {
            'type': 'ir.actions.act_window',
            'name': 'Order',
            'res_model': 'sale.order',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'views': [
                (form_view or False, 'form'), 
                ],
            #'domain': [('id', 'in', item_ids)],
            'target': 'new',
            'context': {'minimal_view': True},
            }
            
    def open_original(self, cr, uid, ids, context=None):
        ''' Open original order
        '''
        return {
            'type': 'ir.actions.act_window',
            'name': 'Order',
            'res_model': 'sale.order',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form,tree',
            #'view_id': view_id,
            #'target': 'new',
            #'nodestroy': True,
            #'domain': [('product_id', 'in', ids)],
            }
        
    # Procedure to update
    def force_parameter_for_delivery(self, cr, uid, ids, context=None):
        ''' Compute all not closed order for delivery
        '''
        # Call new function:
        # Close order:
        self.scheduled_check_close_order(cr, uid, context=context)
        return self.scheduled_clean_for_readability_order(
            cr, uid, context=context)

    def force_parameter_for_delivery_one(self, cr, uid, ids, context=None):
        ''' Compute all not closed order for delivery
        '''        
        context = context or {}
        context['force_one'] = ids[0]

        # TODO close order:
        # Call new function:
        return self.scheduled_clean_for_readability_order(
            cr, uid, context=context)

    # -----------------
    # Scheduled events:
    # -----------------
    # XXX change: now doesn't override event:
    def scheduled_clean_for_readability_order(self, cr, uid, context=None):
        ''' Override original procedure for write all producted
        '''
        if context is None:
            context = {}
            
        force_one = context.get('force_one', False)
        sol_pool = self.pool.get('sale.order.line')
        esit = True

        logfile = '/home/administrator/photo/log/order/readability_todo.log'
        log = []

        # ---------------------------------------------------------------------
        #                       Mark order close and mrp:
        # ---------------------------------------------------------------------
        if force_one:
            order_ids = [force_one]

            log.append('Force one order: %s' % (force_one, ))
            _logger.info(log[-1])
        else:
            # Call original to update closed parameters:
            #super(SaleOrder, self).scheduled_check_close_order(
            #    cr, uid, context=context)
            
            order_ids = self.search(cr, uid, [
                ('state', 'not in', ('cancel', 'sent', 'draft')),
                ('mx_closed', '=', False),
                ], context=context)

            log.append('Force one order: all')
            _logger.info(log[-1])
        
        # --------------------------------
        # All closed are produced in view:
        # --------------------------------
        # Pricelist order are yet set to closed:
        if not order_ids:
            log.append('No order to force!')
            _logger.info(log[-1])
            return True

        log.append('Update production in order (# %s)' % len(order_ids))
        _logger.info(log[-1])
        
        # 4 states:
        update_line = {
            'over': [],
            'delivered': [],
            'produced': [],
            'partial': [],
            'no': [],            
            }
        produced_ids = []

        for order in self.browse(cr, uid, order_ids, context=context):
            all_produced = True
            for line in order.order_line:
                remain = line.product_uom_qty - line.delivered_qty
                # Produced + assigned
                produced = \
                    line.product_uom_maked_sync_qty + line.mx_assigned_qty
                
                if remain <= 0.0: # all delivered:
                    update_line['delivered'].append(line.id)
                else: # Check type of operation:
                    # ---------------------------------------------------------
                    # stock:
                    # ---------------------------------------------------------
                    if line.delivered_qty > produced: 
                        if line.product_uom_qty <= line.delivered_qty:
                            update_line['delivered'].append(line.id)
                        else:
                            update_line['partial'].append(line.id)
                            all_produced = False
                    # ---------------------------------------------------------
                    # mrp:
                    # ---------------------------------------------------------
                    else:
                        if line.product_uom_qty <= produced:
                            update_line['produced'].append(line.id)
                        elif produced > line.delivered_qty:                           
                            update_line['partial'].append(line.id)
                            all_produced = False
                        else:
                            update_line['no'].append(line.id)
                            all_produced = False
            if all_produced:
                produced_ids.append(order.id)

        closed_state = ('delivered', 'over')
        for key in update_line:
            if update_line[key]:
                data = {
                    'mrp_production_state': key,
                    }
                if key in closed_state:
                    data.update({'mx_closed': True})
                    
                sol_pool.write(
                    cr, uid, update_line[key], data, context=context)

                log.append('Line %s delivered (# %s)' % (
                    key, len(update_line[key])))
                _logger.info(log[-1])
               
        if produced_ids:
            self.write(cr, uid, produced_ids, {
                'all_produced': True,
                }, context=context)
            log.append('Order all produced (# %s)' % len(produced_ids))
            _logger.info(log[-1])

        # ---------------------------------------------------------------------
        # Update readability parameter in line
        # ---------------------------------------------------------------------
        log.append('Readability parameter')
        _logger.info(log[-1])

        # Pricelist order are set to closed:        
        if force_one:
            order_ids = [force_one]
        else:        
            order_ids = self.search(cr, uid, [
                ('state', 'not in', ('cancel', 'sent', 'draft')),
                ('mx_closed', '=', False),
                ], context=context)

        log.append('Update %s order...' % len(order_ids))
        _logger.info(log[-1])
        i = 0
        for order in self.browse(cr, uid, order_ids, context=context):
            i += 1
            log.append('%s order update: %s' % (i, order.name))
            _logger.info(log[-1])
                
            # Order counter:
            order_ml_part = 0.0
            order_ml_tot = 0.0
            order_volume_tot = 0.0
            order_volume_part = 0.0
            order_amount_b = 0.0
            order_amount_s = 0.0

            write_error = False            
            write_error_order = []
            for line in order.order_line:
                if line.mrp_production_state == 'delivered':
                    sol_pool.write(cr, uid, line.id, {
                        'delivery_oc': 0,
                        'delivery_b': 0,
                        'delivery_s': 0,
                        'delivery_ml_total': 0,
                        'delivery_ml_partial': 0,
                        'delivery_vol_total': 0,
                        'delivery_vol_partial': 0,
                        }, context=context)
                    continue

                # TODO manage over delivery!!!!
                delivery_oc = line.product_uom_qty - line.delivered_qty
                produced = \
                    line.product_uom_maked_sync_qty + line.mx_assigned_qty
                if produced > line.delivered_qty: 
                    # MRP:
                    delivery_b = produced - line.delivered_qty
                    delivery_s = delivery_oc - delivery_b
                else:    
                    # STOCK:
                    delivery_b = 0.0
                    delivery_s = delivery_oc
                
                ml = line.product_id.linear_length or 0.0
                volume = line.product_id.volume or 0.0
                
                delivery_ml_total = delivery_oc * ml
                delivery_ml_partial = delivery_b * ml
                delivery_vol_total = delivery_oc * volume
                delivery_vol_partial = delivery_b * volume

                # Total for order:
                if line.product_uom_qty:
                    order_amount_b += delivery_b * line.price_subtotal / \
                        line.product_uom_qty
                    order_amount_s += delivery_s * line.price_subtotal / \
                        line.product_uom_qty
                        
                order_ml_tot += delivery_ml_total
                order_ml_part += delivery_ml_partial
                order_volume_tot += delivery_vol_total
                order_volume_part += delivery_vol_partial

                try:                    
                    sol_pool.write(cr, uid, line.id, {
                        'delivery_oc': delivery_oc,
                        'delivery_b': delivery_b,
                        'delivery_s': delivery_s,
                        'delivery_ml_total': delivery_ml_total,
                        'delivery_ml_partial': delivery_ml_partial,
                        'delivery_vol_total': delivery_vol_total,
                        'delivery_vol_partial': delivery_vol_partial,
                        }, context=context)
                except:
                    write_error = True
                    esit = False
                    log.append('Write error line, order %s' % order.name)
                    _logger.info(log[-1])

                    if order.id not in write_error_order:
                        write_error_order.append(order.id)
                    break # stop writing line
                    
            try:
                if not write_error:
                    self.write(cr, uid, order.id, {
                        'delivery_amount_b': order_amount_b,
                        'delivery_amount_s': order_amount_s,
                        'delivery_amount_oc': order_amount_s + order_amount_b,

                        'delivery_ml_total': order_ml_tot,
                        'delivery_ml_partial': order_ml_part,
                        'delivery_vol_total': order_volume_tot,
                        'delivery_vol_partial': order_volume_part,
                        }, context=context)
                else:
                    esit = False
                    log.append('>> order not write: %s' % order.name)
                    _logger.info(log[-1])
                
            except:
                if order.id not in write_error_order:
                    log.append('Write error order: %s' % order.name)
                    _logger.info(log[-1])
                    write_error_order.append(order.id)
                    esit = False
                continue

        if write_error_order:
            log.append('Write error order: %s' % (write_error_order, ))
            _logger.info(log[-1])

        log.append('Total order updated')
        _logger.info(log[-1])
        try:
            log_f = open(logfile, 'a')
            log_f.write('\n************* INIZIO SCHEDULAZIONE **************')
            log_f.write('\n'.join(log))
            log_f.close()
        except:
            _logger.error('Error write log file: %s' % logfile)
        return esit
    
    def _function_get_remain_order(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = [
                line.id for line in order.order_line if line.delivery_oc > 0]
                #if line.product_uom_qty > line.delivered_qty
        return res

    def mark_as_delivering(self, cr, uid, ids, context=None):
        ''' Set as delivering
        '''
        return self.write(cr, uid, ids, {
            'delivering_status': True,
            }, context=None)

    def mark_as_no_delivering(self, cr, uid, ids, context=None):
        ''' Set as no delivering
        '''
        return self.write(cr, uid, ids, {
            'delivering_status': False,
            }, context=None)
        
    _columns = {
        'delivering_status': fields.boolean('Delivering status'),
        'all_produced': fields.boolean('All produced'),
        
        # Total:
        'delivery_amount_b': fields.float('Amount B', digits=(16, 2)),             
        'delivery_amount_s': fields.float('Amount S', digits=(16, 2)),
        'delivery_amount_oc': fields.float('Residuo OC', digits=(16, 2)),

        'delivery_ml_total': fields.float('m/l tot', digits=(16, 2)),             
        'delivery_ml_partial': fields.float('m/l part', digits=(16, 2)),
        'delivery_vol_total': fields.float('vol. tot', digits=(16, 2)),
        'delivery_vol_partial': fields.float('vol. part', digits=(16, 2)),             

        'remain_order_line': fields.function(_function_get_remain_order, 
            method=True, type='one2many', string='Residual order line', 
            relation='sale.order.line', store=False), 
        }

class SaleOrderLine(orm.Model):
    """ Model name: SaleOrderLine
    """
    _inherit = 'sale.order.line'
    
    def nothing(self, cr, uid, ids, context=None):
        '''  do nothing
        '''
        return True

    _columns = {
        'mrp_production_state': fields.selection([
            ('over', 'Over delivered'), # XXX no more used
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
