# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


import os
import sys
import logging
import openerp
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class SaleDeliveryPartialWizard(orm.TransientModel):
    ''' Wizard for partial delivery on sale
    '''
    _name = 'sale.delivery.partial.wizard'

    # -------------------------------------------------------------------------
    #                             Wizard button event
    # -------------------------------------------------------------------------
    def setup_deliver_remain_qty(self, cr, uid, ids, with_deadline, 
            context=None):
        ''' Function used from 2 button as set up remain q, depend or not 
            from date deadline value
        '''    
        assert len(ids) == 1, 'Button work only with one record a time!'
        
        line_pool = self.pool.get('sale.delivery.partial.line.wizard')
        
        # Set all line delivery q. to remain q
        item_proxy = self.browse(cr, uid, ids, context=context)[0]
        updated = 0
        for line in item_proxy.line_ids:
            # Deadline check:
            if not with_deadline or \
                    line.date_deadline == item_proxy.date_deadline:
                # Set remain q.:    
                line_pool.write(cr, uid, line.id, {
                    'delivery_uom_qty': line.product_remain_qty,
                    }, context=context)
                updated += 1    

        if updated:
            # Call delivery button:                
            return self.action_delivery(cr, uid, ids, context=context)    
        else: # Raise error:
            raise osv.except_osv(
                _('Error!'),
                _('No elements to update, change remain q. or deadline!'))
    
    # Utility:
    def deliver_remain_qty(self, cr, uid, ids, context=None):
        ''' Set remain qty to pick out quantity
        '''
        return self.setup_deliver_remain_qty(cr, uid, ids, with_deadline=False, 
            context=context) 
    
    def deliver_remain_deadline_qty(self, cr, uid, ids, context=None):
        ''' Set remain qty to pick out quantity
        '''
        return self.setup_deliver_remain_qty(cr, uid, ids, with_deadline=True, 
            context=context) 
    
    def action_delivery(self, cr, uid, ids, context=None):
        ''' Event for button done the delivery
        '''
        assert len(ids) == 1, 'Button work only with one record a time!'

        if context is None: 
            context = {}
        
        # Pool used:
        sale_pool = self.pool.get('sale.order')
        
        # Proxy used:
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        
        # Generate line to pick out:
        pick_line_ids = {}
        _logger.info(wiz_browse.line_ids)
        for line in wiz_browse.line_ids:
            if line.all_qty: # checked delivery remain:
                pick_line_ids[
                    line.order_line_id.id] = line.product_remain_qty            
                # TODO REMOVE LOG    
                #_logger.warning('prod: %s seq.: %s id: %s q.: %s' % (
                #    line.order_line_id.product_id.default_code,                    
                #    line.order_line_id.sequence,
                #    line.order_line_id.id,
                #    pick_line_ids[line.order_line_id.id],
                #    ))
            else:    
                pick_line_ids[
                    line.order_line_id.id] = line.delivery_uom_qty
                # TODO REMOVE LOG    
                #_logger.warning('prod: %s seq.: %s id: %s q.: %s' % (
                #    line.order_line_id.product_id.default_code,                    
                #    line.order_line_id.sequence,
                #    line.order_line_id.id,
                #    pick_line_ids[line.order_line_id.id],
                #    ))
        
        # Create pick out with new procedure (not standard):
        context['force_date_deadline'] = wiz_browse.date_deadline or False
        
        _logger.warning('Create pick with this order: %s' % (pick_line_ids))
        picking_id = sale_pool._create_pickings_from_wizard(
            cr, uid, wiz_browse.order_id, pick_line_ids, 
            context=context)
            
        # TODO return new order:
        return {'type': 'ir.actions.act_window_close'}

    def force_deadline_delivery(self, cr, uid, ids, context=None):
        ''' Set up line that have to be delivered depend on date
        '''
        if context is None: 
            context = {}
        #TODO
        return True    

    _columns = {
        'order_id': fields.many2one('sale.order', 'Order ref.', readonly=True),
        'date_deadline': fields.date('Deadline', 
            help='Used for force delivery of deadline records'),
        }

class SaleDeliveryPartialLineWizard(orm.TransientModel):
    ''' Temp object for document line
    '''
    _name = 'sale.delivery.partial.line.wizard'

    # On change event:
    def onchange_delivery_qty(self, cr, uid, ids, 
            delivery_uom_qty, product_remain_qty, context=None):
        ''' Check that delivered not greater that remain
        '''    
        context = context or {}
        res = {}

        if delivery_uom_qty > product_remain_qty:
            res['warning'] = {
                'title': _('Error'),
                'message': _('Max value admitted: %s' % product_remain_qty),
                }
        return res

    _columns = {
        # Sale order line reference:
        'wizard_id': fields.many2one('sale.delivery.partial.wizard', 
            'Wizard ref.', ondelete='cascade'),
        'order_line_id': fields.many2one('sale.order.line', 'Order line ref.'),
        'sequence': fields.integer(
            'Sequence', readonly=True,
            help="Gives the sequence order when displaying in list mode."),
        'product_id': fields.many2one(
            'product.product', 'Product', domain=[('sale_ok', '=', True)],
            readonly=True),
        'price_unit': fields.float(
            'Unit Price', digits_compute=dp.get_precision('Product Price'), 
            readonly=True),
        'mx_assigned_qty': fields.float(
            'Assigned', digits_compute=dp.get_precision('Product UoS'), 
            readonly=True),
        'product_uom_qty': fields.float(
            'Quantity', digits_compute=dp.get_precision('Product UoS'), 
            readonly=True),
        'product_uom_maked_sync_qty': fields.float(
            'B', digits_compute=dp.get_precision('Product UoS'), 
            readonly=True),
        'product_uom': fields.many2one(
            'product.uom', 'Unit of Measure', readonly=True),
        'date_deadline': fields.date('Deadline', readonly=True),        
        'all_qty': fields.boolean('All'),
        
        # Load during default procedure:
        'product_delivered_qty': fields.float(
            'Delivered', digits_compute=dp.get_precision('Product UoS'), 
            readonly=True),
        'product_remain_qty': fields.float(
            'Remain', digits_compute=dp.get_precision('Product UoS'), 
            readonly=True),

        # Input fields:
        'delivery_uom_qty': fields.float(
            'Delivery q.', digits_compute=dp.get_precision('Product UoS')),
        }

class SaleDeliveryPartialWizard(orm.TransientModel):
    ''' Add *many fields:
    '''
    _inherit = 'sale.delivery.partial.wizard'
                
    def _load_default_line_ids(self, cr, uid, context=None):
        ''' Load order line as default values
        '''
        context = context or {}
        all_qty = context.get('all_qty', False)
        sale_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')
        order_id = context.get('active_id', False)
        if not order_id:
            return False # error
        
        has_b = 'product_uom_maked_sync_qty' in line_pool._columns
        sale_proxy = sale_pool.browse(cr, uid, order_id, context)

        # Read delivered per sale order line (or picked)
        # TODO convert in a function fields?
        # TODO remove:
        #sol_status = {}
        #for pick in sale_proxy.stock_picking_ids :
        #    for line in pick.move_lines:
        #        sol_id = line.sale_line_id.id # TODO correct?
        #        if sol_id not in sol_status:
        #            sol_status[sol_id] = 0.0
        #        sol_status[sol_id] += line.product_uom_qty # TODO uos?
        
        res = []
        lines = 0
        for line in sale_proxy.order_line:                      
            product_delivered_qty = line.delivered_qty #sol_status.get(line.id, 0.0)
            
            if line.product_uom_qty - product_delivered_qty <= 0:
                continue # Jump all delivered qty!
            lines += 1
            if has_b:
                b_qty = line.product_uom_maked_sync_qty
            else:
                b_qty = 0

            res.append((0, False, {
                #'wizard_id': 1,
                'order_line_id': line.id,
                'sequence': line.sequence,
                'product_id': line.product_id.id,
                'price_unit': line.price_unit,
                'product_uom_qty': line.product_uom_qty,
                'mx_assigned_qty': line.mx_assigned_qty,
                'product_uom_maked_sync_qty': b_qty, 
                'product_uom': line.product_uom.id,
                'date_deadline': line.date_deadline,
                'all_qty': all_qty,
                
                # Calculated:
                'product_delivered_qty': product_delivered_qty,
                'product_remain_qty':
                    line.product_uom_qty - product_delivered_qty,
                }))
        if not lines:
            raise osv.except_osv(_('Warning'), _('All delivered!!'))
        return res
        
    _columns = {
        'line_ids': fields.one2many(
            'sale.delivery.partial.line.wizard', 'wizard_id', 'Wizard'), 
        }
    
    _defaults = {
        'line_ids': lambda s, cr, uid, ctx: s._load_default_line_ids(
            cr, uid, ctx)
        }    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


