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


class ProductProduct(orm.Model):
    ''' Append extra fields to product obj
    '''
    _inherit = 'product.product'

    # ---------------
    # Field function:    
    # ---------------
    def _get_report_bom(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate textilene bom, if present
        '''
        res = {}
        mrp_pool = self.pool.get('mrp.bom')
        
        # All 'in report' bom for product passed
        mrp_ids = mrp_pool.search(cr, uid, [
            ('product_id', 'in', ids),
            ('sql_import', '=', True), # TODO change!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #('in_report', '=', True),
            ], context=context)
            
        # TODO problem if bom use template!!!!
        for bom in mrp_pool.browse(cr, uid, mrp_ids, context=context):
            if bom.product_id.id in res:  
                # TODO comunicate the error?
                _logger.error('Bom in report with more than one product')
            else:
                res[bom.product_id.id] = bom.id
        return res
        
    _columns = {
        'not_in_report': fields.boolean('Not in report',
            help='Material that start with T but don\'t need to be track'
                'for textylene material'),
                
        # Raw material:
        'in_report': fields.boolean('In report',
            help='Material that need to be track in report status, used'
                'for textylene material'),
        
        # Product:
        'report_bom_id': fields.function(
            _get_report_bom, method=True, 
            type='many2one', relation='mrp.bom', string='Textilene bom', 
            help='One reference BOM for product (for in report status)',
            store=False),            
        }

class MrpBom(orm.Model):
    ''' Append extra fields to BOM
    '''
    _inherit = 'mrp.bom'
    
    def _in_report_bom(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for bom in self.browse(cr, uid, ids, context=context):
            res[bom.id] = any([
                line.product_id.in_report for line in bom.bom_line_ids])
        return res
        
    _columns = {
        'in_report': fields.function(
            _in_report_bom, method=True, 
            type='boolean', string='In report', store=False, 
            help='If true the bom will be tracked for status report'), 
        }

class MrpBomLine(orm.Model):
    ''' Append extra fields to BOM line
    '''
    _inherit = 'mrp.bom.line'

    _columns = {
        'in_report': fields.related(
            'product_id', 'in_report', type='boolean', 
            string='Product in report', store=False),
        }    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
