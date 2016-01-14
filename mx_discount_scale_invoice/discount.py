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


class AccountInvoice(orm.Model):
    """ Model name: AccountInvoice
    """    
    _inherit = 'account.invoice'
    
    def force_all_multi_discount_rates(self, cr, uid, ids, context=None):
        ''' Force all line with header value
        '''
        line_pool = self.pool.get('account.invoice.line')
        
        header_proxy = self.browse(cr, uid, ids, context=context)[0]
        for line in header_proxy:
            line_pool.write(cr, uid, line.id, {
                'multi_discount_rates': header_proxy.multi_discount_rates
                # TODO also calculate value discount
                #'discount': self._XXXx,
                }, context=context)
    
    _columns = {
        'multi_discount_rates': fields.char('Discount scale', size=30, 
            help='Use for force the one in lines'),
        }

class AccountInvoiceLine(orm.Model):
    """ Model name: AccountInvoiceLine
    """
    
    _inherit = 'account.invoice.line'
    
    _columns = {
        'multi_discount_rates': fields.char('Discount scale', size=30),
        'price_use_manual': fields.boolean('Use manual net price',
            help='If specificed use manual net price instead of '
                'lord price - discount'),
        'price_unit_manual': fields.float(
            'Manual net price', digits_compute=dp.get_precision('Sale Price')),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
