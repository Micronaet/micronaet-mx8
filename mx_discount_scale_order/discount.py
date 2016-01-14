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


class ResPartner(orm.Model):
    ''' Model name: ResPartner
    '''    
    _inherit = 'res.partner'
    
    _columns = {
        'discount_value': fields.float('Discount value', digits=(16, 2)),
        'discount_rates': fields.char('Discount scale', size=30),
        }

class SaleOrder(orm.Model):
    ''' Model name: SaleOrder
    '''
    
    _inherit = 'sale.order'
    
    _columns = {
        'multi_discount_rates': fields.char('Discount scale', size=30, 
            help='Use for force the one in lines'),
        }

class SaleOrderLine(orm.Model):
    ''' Model name: SaleOrderLine
    '''
    
    _inherit = 'sale.order.line'
    
    _columns = {
        'multi_discount_rates': fields.char('Discount scale', size=30),
        'price_use_manual': fields.boolean('Use manual net price',
            help='If specificed use manual net price instead of '
                'lord price - discount'),
        'price_unit_manual': fields.float(
            'Manual net price', digits_compute=dp.get_precision('Sale Price')),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
