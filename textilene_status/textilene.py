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

    # -----------------
    # Scheduled action:
    # -----------------
    def send_textilene_report(self, cr, uid, context=None):
        ''' Export as file report and send by email
        '''
        # Utility:
        def clean(filename):
            remove = '/\'\\&"!;,?=:-) (%$£'
            for c in remove:
                if ord(c) > 127:
                    continue # jump not ascii char
                filename = filename.replace(c, '_')           
            return filename
            
        # attachment_obj = self.pool.get('ir.attachment')
        partner_pool = self.pool.get('res.partner') # non necessary
        action_pool = self.pool.get('ir.actions.report.xml')
        date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # Parameter:
        report_name = 'stock_status_fabric_report'
        
        report_service = 'report.%s' % report_name
        service = netsvc.LocalService(report_service)
        
        # Call report:            
        (result, extension) = service.create(
            cr, uid, [1], {'model': 'res.partner'}, context=context)
            
        # Generate file:    
        filename = '/tmp/tx_status_%s.%s' % (
            date,
            extension,
            )
        file_pdf = open(filename, 'w')
        file_pdf.write(result)
        file_pdf.close()
        
        # Send mail with attachment:
        group_pool = self.pool.get('res.groups')
        model_pool = self.pool.get('ir.model.data')
        thread_pool = self.pool.get('mail.thread')
        group_id = model_pool.get_object_reference(
            cr, uid, 'textilene_status', 'group_textilene_admin')[1]    
        partner_ids = []
        for user in group_pool.browse(
                cr, uid, group_id, context=context).users:
            partner_ids.append(user.partner_id.id)
            
        thread_pool = self.pool.get('mail.thread')
        thread_pool.message_post(cr, uid, False, 
            type='email', 
            body='Textilente status', 
            subject='TX Report: %s' % date,
            partner_ids=[(6, 0, partner_ids)],
            attachments=[
                ('Report_%s.%s' % (date, extension), result)], context=context
            )
        return True

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

class ResCompany(orm.Model):
    """ Model name: ResCompany
    """    
    _inherit = 'res.company'
    
    _columns = {
        # Load unload normal:
        'stock_report_tx_load_in_ids': fields.many2many(
            'stock.picking.type', 'company_tx_load_in_rel', 
            'company_id', 'type_id',
            'Load TX in type'),             
        'stock_report_tx_load_out_ids': fields.many2many(
            'stock.picking.type', 'company_tx_load_out_rel', 
            'company_id', 'type_id', 
            'Load TX out type'),

        # Document for load unload production:    
        'stock_report_tx_mrp_in_ids': fields.many2many(
            'stock.picking.type', 'company_tx_mrp_in_rel', 
            'company_id', 'type_id',
            'MRP. TX in type'),             
        'stock_report_tx_mrp_out_ids': fields.many2many(
            'stock.picking.type', 'company_tx_mrp_out_rel', 
            'company_id', 'type_id', 
            'MRP. TX out type'),
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
