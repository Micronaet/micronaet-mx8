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


class SaleOrderDelivery(orm.Model):
    """ Model name: SaleOrderDelivery
    """
    _name = 'sale.order.delivery'
    _description = 'Sale order delivery'
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'create_date': fields.date('Create date', readonly=True),
        'create_uid': fields.many2one('res.users', 'Create user', 
            readonly=True), 
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True), 
        'note': fields.text('Note'),
        'state': fields.selection([
            ('draft', 'Draft'), ('done', 'Done'),
            ], 'State', readonly=True),
        }
    
    _defaults = {
        'name': lambda *a: _('Multi delivery of: %s' % (
            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))),
        'state': lambda *x: 'draft',
        }

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order'
    
    _columns = {
        'multi_delivery_id': fields.many2one(
            'sale.order.multidelivery', 'Multi delivery', ondelete='set null'), 
        }

class SaleOrderLine(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order.line'
    
    def _get_move_lines(self, cr, uid, ids, context=None):
        ''' When change ref. in order also in lines
        '''
        sale_pool = self.pool['sale.order']
        res = []
        for sale in sale_pool.browse(cr, uid, ids, context=context):
            for line in sale.order_line:
                res.append(line.id)
        return res
    
    _columns = {
        'multi_delivery_id': fields.related(
            'order_id', 'multi_delivery_id', 
            type='many2one', relation='sale.order.delivery', 
            string='Multi delivery', store={
                # Auto change if moved line in other order:
                'sale.order.line': (
                    lambda self, cr, uid, ids, c=None: ids,
                    ['order_id'],
                    10),
                # Wneh change in order header value:    
                'sale.order': (
                    _get_move_lines,
                    ['multi_delivery_id'],
                    10),
                }),
        }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
