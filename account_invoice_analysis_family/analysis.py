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
    
    def _get_family_id_from_line(self, cr, uid, ids, context=None):
        ''' When change product in invoice line change family
        '''
        _logger.warning('Change product in invoice line, so family')
        return ids
        
    def _get_family_id_from_product(self, cr, uid, ids, context=None):
        ''' Change family in product
        '''
        line_pool = self.pool.get('account.invoice.line')
        line_ids = line_pool.search(cr, uid, [
            ('product_id', 'in', ids),
            ], context=context)
        _logger.warning('Change family product so family in invoice line')
        return line_ids
        
    _columns = {
        'family_id': fields.related(
            'product_id', 'family_id', type='many2one', 
            relation='product.template', 
            store={
                'account.invoice.line':
                    (_get_family_id_from_line, ['product_id'], 10),
                'product.product':
                     (_get_family_id_from_product, ['family_id'], 10),
                }, string='Family',      
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
