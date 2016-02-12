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


class SaleOrderLine(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order.line'
    
    # Override for use production test 
    # TODO change when quants!!!!!!!  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    def set_all_qty(self, cr, uid, ids, context=None):
        ''' Set qty depend on remain (overridable from MRP!!!)
        '''
        assert len(ids) == 1, 'Only one line a time'
        
        line_proxy = self.browse(cr, uid, ids, context=context)[0]
        if line_proxy.is_manufactured:
            if line_proxy.product_uom_maked_sync_qty < line_proxy.delivered_qty:
                # Use manual!!
                raise osv.except_osv(
                    _('Error'), 
                    _('Stock is used! Write manual to deliver qty!'))                    
        
            to_deliver_qty = line_proxy.product_uom_maked_sync_qty - \
                line_proxy.delivered_qty
        else:        
            to_deliver_qty = line_proxy.product_uom_qty - \
                line_proxy.delivered_qty

        if to_deliver_qty:
            return self.write(cr, uid, ids, {
                'to_deliver_qty': to_deliver_qty,
                }, context=context)
        else:
            raise osv.except_osv(
                _('Warning'), 
                _('0 was move, no stock, try set manual!'))
                


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
