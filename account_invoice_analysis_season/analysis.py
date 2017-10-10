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

class AccountInvoiceLine(orm.Model):
    """ Model name: AccountInvoiceLine
    """    
    _inherit = 'account.invoice.line'
    
    def _get_season_from_date(self, date_invoice):
        ''' Return season from date
        '''
        start_month = '09'
        if not date_invoice:
            return False
        current_month = date_invoice[5:7]
        year = int(date_invoice[2:4])
        if current_month >= start_month: # [09 : 12]
            return '%02d-%02d' % (year, year + 1)
        else: # [01 : 08]
            return '%02d-%02d' % (year - 1, year)
                
    def _get_season_from_invoice_line(self, cr, uid, ids, context=None):
        ''' Change family in product
        '''
        line_pool = self.pool.get('account.invoice.line')
        line_ids = line_pool.search(cr, uid, [
            ('invoice_id', 'in', ids),
            ], context=context)
        _logger.warning('Change season invoice line as invoice change date')
        return line_ids
        
    # -------------------------------------------------------------------------    
    # Field function:    
    # -------------------------------------------------------------------------    
    def _get_season_from_invoice_date(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = self._get_season_from_date(
                line.invoice_id.date_invoice)
        return res

    _columns = {
        'season_period': fields.function(
            _get_season_from_invoice_date, method=True, 
            type='char', size=30, string='Season', 
            store={
                'account.invoice':
                    (_get_season_from_invoice_line, ['date_invoice'], 10),
                }
            )     
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
