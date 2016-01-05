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

class StockMove(orm.Model):
    """ Model name: Stock Move
    """    
    _inherit = 'stock.move'

    _columns = {
        'virtual_move': fields.boolean('Virtual move', 
            help='used for keep virtual quantity correctly indicated'),
        
        # TODO used?    
        'virtual_sale_id': fields.many2one(
            'sale.order.line', 'Virtual sale line', ondelete='set null',
            help='Sale order line linked (for virtual availability calc)'),
        'virtual_purchase_id': fields.many2one(
            'stock.move', 'Virtual purchase line', ondelete='set null',
            help='Purchase order line linked (for virtual availability calc)'),
        }

class SaleOrder(orm.Model):
    """ Model name: Sale order
    """    
    _inherit = 'sale.order'

    '''def write(self, cr, uid, ids, vals, context=None):
        """ Update record(s) comes in {ids}, with new value comes as {vals}
            return True on success, False otherwise
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of record ids to be update
            @param vals: dict of new values to be set
            @param context: context arguments, like lang, time zone
            
            @return: True on success, False otherwise
        """
    
        #TODO: process before updating resource
        res = super(SaleOrder, self).write(
            cr, uid, ids, vals, context=context)
        
        # TODO only for one:    
        order_proxy = self.browse(cr, uid, ids, context=context)[0]
        if order_proxy.state in ('cancel', 'sent', 'cancel'):
            return res
            
        _logger.info('WRITE OPERATION ON ORDER')
        # TODO recalculate virtual    
        return res'''
    
    
    # Utility:    
    def _create_update_virtual_move(self, cr, uid, ids, context=None):
        ''' Confirm as usual order after create virtual stock move line for
            availablity with order
        '''
        stock_pool = self.pool.get('stock.move')
        line_pool = self.pool.get('sale.order.line')

        order = self.browse(cr, uid, ids, context=context)[0]

        for line in order.order_line:
            # Virtual ordered qty:
            virtual_qty = line.product_uom_qty - line.delivered_qty
            if virtual_qty < 0.0:
                virtual_qty = 0.0 # XXX for negative control

            if line.remain_move_id: # create only once
                stock_pool.write(cr, uid, {
                    'product_uom_qty': virtual_qty,                    
                    }, context=context)                
                continue
    
            move_data = self._prepare_order_line_move(
                cr, uid, order, line, False,
                order.date_confirm, context=context) # XXX before date_planned
                
            # Add extra information in move:
            move_data['virtual_move'] = True
            move_data['product_uom_qty'] = virtual_qty
            move_data['state'] = 'assigned' # TODO force here?!?
            move_data['virtual_sale_id'] = line.id
            # Remove link for sale line (instead calculate delivered qty)
            del(move_data['sale_line_id']) 
            
            # TODO check Q. als for UOM!   

            move_id = stock_pool.create(cr, uid, move_data, context=context)
            line_pool.write(cr, uid, line.id, {
                'remain_move_id': move_id,
                }, context=context)        
        return True

    # Override confirm for create stock.move line
    def action_button_confirm(self, cr, uid, ids, context=None):
        ''' Override to create stock.move
        '''
        res = super(SaleOrder, self).action_button_confirm(
            cr, uid, ids, context=context)
        return res # TODO remove
        # Create virtual movement for availability:    
        self._create_update_virtual_move(cr, uid, ids, context=context)
        return res
    
class SaleOrderLine(orm.Model):
    """ Model name: Sale line
    """    
    _inherit = 'sale.order.line'
    
    '''def write(self, cr, uid, ids, vals, context=None):
        """ Update redord(s) comes in {ids}, with new value comes as {vals}
            return True on success, False otherwise
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of record ids to be update
            @param vals: dict of new values to be set
            @param context: context arguments, like lang, time zone
            
            @return: True on success, False otherwise
        """    
        res = super(SaleOrderLine, self).write(
            cr, uid, ids, vals, context=context)
        
        # TODO check in there's quantity for update stock.move line
        return res'''
    
    '''def unlink(self, cr, uid, ids, context=None):
        """ Delete all record(s) from table heaving record id in ids
            return True on success, False otherwise 
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of record ids to be removed from table
            @param context: context arguments, like lang, time zone
            
            @return: True on success, False otherwise
        """
        # TODO delete stock.move before (use ondelete?
        res = super(SaleOrderLine, self).unlink(
            cr, uid, ids, context=context)
        return res'''    
    
    _columns = {
        'remain_move_id': fields.many2one(
            'stock.move', 'Remain move', ondelete='cascade'), 
        }
    
class PurchaseOrderLine(orm.Model):
    """ Model name: Purchase line
    """    
    _inherit = 'purchase.order.line'
    
    _columns = {
        'remain_move_id': fields.many2one(
            'stock.move', 'Remain move', ondelete='cascade'),
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
