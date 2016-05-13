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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
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
    """ Model name: SaleOrder for selection
    """    
    _inherit = 'sale.order'
    
    # -------------------------------------------------------------------------
    # Utility to use this many2many field:
    # -------------------------------------------------------------------------

    # -------------
    # Button press:
    # -------------
    def print_off_set_user_order(self, cr, uid, ids, context=None):
        ''' Set to print for order passed and user selected        
        '''
        return self.write(cr, uid, ids, {
            'print_ids': [(3, uid)],
            }, context=context)

    def print_on_set_user_order(self, cr, uid, ids, context=None):
        ''' Set to print for order passed and user selected        
        '''
        return self.write(cr, uid, ids, {
            'print_ids': [(4, uid, False)],
            }, context=context)

    def _get_print_test(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        ''' 
        res = {}   
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = uid in [item.id for item in order.print_ids]
        return res

    def _get_search_print_test(self, cr, uid, ids, fields, args, context=None):            
        ''' Fields function for calculate for search purpose
        '''
        user_pool = self.pool.get('res.users')
        user_proxy = user_pool.browse(cr, uid, uid, context=context)
        # TODO append current?
        order_list = [order.id for order in user_proxy.order_print_ids]
        return [('id', 'in', order_list)]

    def reset_print(self, cr, uid, ids, context=None):
        ''' Called at the end of report to reset print check
        '''
        cr.execute('''
            delete from order_user_selection_rel where user_id=%s;
            ''', (uid, ))

    _columns = {
        'print_ids': fields.many2many(
            'res.users', 'order_user_selection_rel', 
            'order_id', 'user_id', 'Print selection'),
            
        # XXX Override function:    
        'print': fields.function(
            _get_print_test, fnct_search=_get_search_print_test, 
            method=True, type='boolean', string='To print', 
            store=False),                         
        }

class ResUsers(orm.Model):
    """ Model name: Order selected from users
    """    
    _inherit = 'res.users'

    _columns = {
        'order_print_ids': fields.many2many(
            'sale.order', 'order_user_selection_rel', 
            'user_id', 'order_id', 'Print selection'), 
        }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
