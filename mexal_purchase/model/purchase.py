# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    Original module for stock.move from:
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class StockPicking(orm.Model):
    ''' BF number
    '''
    _inherit = 'stock.picking'
    
    _columns = {
        'bf_number': fields.char('BF number', size=64), 
        'ff_number': fields.char('FF number', size=64), 
        }
        

class PurchaseOrder(orm.Model):
    ''' Purchase extra field
    '''
    _inherit = 'purchase.order'
        
    _columns = {
        # TODO Needed all?
        'carriage_condition_id': fields.many2one(
            'stock.picking.carriage_condition', 'Carriage Condition'),
        'goods_description_id': fields.many2one(
            'stock.picking.goods_description', 'Description of Goods'),
        'transportation_reason_id': fields.many2one(
            'stock.picking.transportation_reason',
            'Reason for Transportation'),
        'transportation_method_id': fields.many2one(
            'stock.picking.transportation_method',
            'Method of Transportation'),
        #'parcels': fields.integer('Number of Packages'),

        'used_bank_id': fields.many2one('res.partner.bank', 'Used bank',
            help='Partner bank account used for payment'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
