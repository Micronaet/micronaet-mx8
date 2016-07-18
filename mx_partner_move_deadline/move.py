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
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'pay_days_fix_delivery': fields.integer('Fix delivery', 
            help='''Fixed delivery, override payment data, ex.:
                1: start, 31: end name, 10: 10 days of month'''),
        'pay_days_fix_delivery_extra': fields.integer('Fix delivery extra',
            help='Fixed delivery extra days add days to delivery'),
        'pay_days_m1': fields.integer('Number of month 1',
            help='Particular month 1'),
        'pay_days_m1_days': fields.integer('Month 1 days',
            help='Extra days for month 1 (+ or - days)'),
        'pay_days_m2': fields.integer('Number of month 2',
            help='Particular month 2'),
        'pay_days_m2_days': fields.integer('Month 2 days',
            help='Extra days for month 2 (+ or - days)'),
        }
    
    _defaults = {
        #'pay_days_m1': lambda *a: 8,
        #'pay_days_m2': lambda *a: 12,
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
