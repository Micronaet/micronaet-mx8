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

class SaleOrder(orm.Model):
    ''' Model name: SaleOrder
    '''    
    _inherit = 'sale.order'
    
    _columns = {
        'fast_vector': fields.boolean('Fast Vector', 
            help='Add fast vector for report and not the one in carrier'),
        'vector_name': fields.char('Vector name'),
        'vector_street': fields.char('Street'),
        'vector_street2': fields.char('Street2'),
        'vector_zip': fields.char('Zip', size=24),
        'vector_city': fields.char('City'),
        'vector_state_id': fields.many2one('res.country.state', 'State', 
            ondelete='restrict'),
        'vector_country_id': fields.many2one('res.country', 'Country', 
            ondelete='restrict'),
        }    

class AccountInvoice(orm.Model):
    ''' Model name: AccountInvoice
    '''    
    _inherit = 'account.invoice'
    
    _columns = {
        'fast_vector': fields.boolean('Fast Vector', 
            help='Add fast vector for report and not the one in carrier'),
        'vector_name': fields.char('Vector name'),
        'vector_street': fields.char('Street'),
        'vector_street2': fields.char('Street2'),
        'vector_zip': fields.char('Zip', size=24),
        'vector_city': fields.char('City'),
        'vector_state_id': fields.many2one('res.country.state', 'State', 
            ondelete='restrict'),
        'vector_country_id': fields.many2one('res.country', 'Country', 
            ondelete='restrict'),
        }

class StockDdt(orm.Model):
    ''' Model name: Stock DDT
    '''    
    _inherit = 'stock.ddt'
    
    _columns = {
        'fast_vector': fields.boolean('Fast Vector', 
            help='Add fast vector for report and not the one in carrier'),
        'vector_name': fields.char('Vector name'),
        'vector_street': fields.char('Street'),
        'vector_street2': fields.char('Street2'),
        'vector_zip': fields.char('Zip', size=24),
        'vector_city': fields.char('City'),
        'vector_state_id': fields.many2one('res.country.state', 'State', 
            ondelete='restrict'),
        'vector_country_id': fields.many2one('res.country', 'Country', 
            ondelete='restrict'),
        }

        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
