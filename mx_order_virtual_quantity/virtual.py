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
        }
    
class SaleOrderLine(orm.Model):
    """ Model name: Sale line
    """    
    _inherit = 'sale.order.line'
    
    def create(self, cr, uid, vals, context=None):
        """ Create a new record for a model SaleOrderLine
            @param cr: cursor to database
            @param uid: id of current user
            @param vals: provides a data for new record
            @param context: context arguments, like lang, time zone
            
            @return: returns a id of new record
        """    
        # Create before:
        res_id = super(SaleOrderLine, self).create(
            cr, uid, vals, context=context)
        # TODO remove!!! ******************************************************
        return res_id    

        order_pool = self.pool.get('sale.order')
        stock_pool = self.pool.get('stock.move')

        order = order_pool.browse(cr, uid, vals.get('order_id'), 
            context=context)
        line = self.browse(cr, uid, res_id, context=context)
            
        # TODO Create stock.move with remain quantity:        
        move_data = order_pool._prepare_order_line_move(
            cr, uid, order, line, False, 
            order.date_planned, context=context)
        # TODO check Q.!    
        stock_pool.create(cr, uid, move_data, context=context)
        return res_id
    
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
        res = super(SaleOrderLine, self).write(
            cr, user, ids, vals, context=context)
        
        # TODO check in there's quantity for update stock.move line
        return res
    
    def unlink(self, cr, uid, ids, context=None):
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
        return res    
    
    
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
