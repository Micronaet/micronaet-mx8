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

    # -------------------------------------------------------------------------
    # Store function:
    # -------------------------------------------------------------------------
    def _store_related_get_line_marketed(self, cr, uid, ids, context=None):
        ''' Change marketed in product
        '''
        _logger.warning('Change product_id in account.invoice.line')
        return ids

    def _store_related_get_marketed(self, cr, uid, ids, context=None):
        ''' Change marketed in product
        '''
        _logger.warning('Change marketed in product.product')
        return self.pool.get('account.invoice.line').search(cr, uid, [
            ('product_id', 'in', ids),
            ], context=context)
    
    _columns = {
        # TODO outsource also?!?
        'marketed': fields.related(
            'product_id', 'marketed', 
            type='boolean', string='Marketed', store={
                'product.product':
                    (_store_related_get_marketed, ['marketed'], 10),
                'account.invoice.line':
                    (_store_related_get_line_marketed, ['product_id'], 10),                    
                }),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
