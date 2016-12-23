# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import openerp
import xlsxwriter # XLSX export
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class StockStatusPrintImageReportWizard(orm.TransientModel):
    ''' Wizard for print stock status
    '''
    _name = 'stock.status.print.image.report.wizard'

    def extract_xls_inventory_file(self, cr, uid, ids, data=None, 
            context=None):
        ''' Extract inventory as XLS extranal files every category in different
            page
        '''        
        # ---------------------------------------------------------------------
        # Utility: 
        # ---------------------------------------------------------------------
        def write_header(current_WS, header):
            ''' Write header in first line:            
            '''
            col = 0
            for title in header:
                current_WS.write(0, col, title)
                col += 1
            return     
            
        # ---------------------------------------------------------------------
        #                        XLS log export:        
        # ---------------------------------------------------------------------
        filename = '/home/administrator/photo/xls/inventory_table.xlsx'
        WB = xlsxwriter.Workbook(filename)

        # ---------------------------------------------------------------------
        # Search all inventory category:
        # ---------------------------------------------------------------------
        inv_pool = self.pool.get('product.product.inventory.category')
        inv_ids = inv_pool.search(cr, uid, [], context=context)

        # ---------------------------------------------------------------------
        # Create work sheet:
        # ---------------------------------------------------------------------
        header = ['DB', 'CODICE', 'DESCRIZIONE', 'UM', 'CAT. STAT.', 
            'CATEGORIA', 'FORNITORE', 'ESISTENZA']
        
        # Create elemnt for empty category:
        WS = {
            #ID: worksheet, counter
            0: [WB.add_worksheet('Non assegnati'), 1],
            }
        write_header(WS[0][0], header)
            
        # Create all others category:    
        for category in inv_pool.browse(
                cr, uid, inv_ids, context=context):
            WS[category.id] = [WB.add_worksheet(category.name), 1]
            write_header(WS[category.id][0], header)
            
        # ---------------------------------------------------------------------
        # Prepare BOM check
        # ---------------------------------------------------------------------
        line_pool = self.pool.get('mrp.bom.line')
        line_ids = line_pool.search(cr, uid, [
            ('bom_id.bom_category', 'in', ('parent', 'dynamic', 'half')),
            ], context=context)

        in_bom_ids = [item.product_id.id for item in line_pool.browse(
            cr, uid, line_ids, context=context)]
                
        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        for product in self.pool.get(
                'product.product').stock_status_report_get_object(
                    cr, uid, data=data, context=context):
            if product.inventory_category_id.id in WS:
                record = WS[product.inventory_category_id.id]
            else:
                record = WS[0]
            
            # Write data in correct WS:
            record[0].write(record[1], 0, 
                'X' if product.id in in_bom_ids else '')
            record[0].write(record[1], 1, product.default_code)
            record[0].write(record[1], 2, product.name)
            record[0].write(record[1], 3, product.uom_id.name or '')
            record[0].write(record[1], 4, product.statistic_category or '')            
            record[0].write(record[1], 5, product.categ_id.name or '')
            record[0].write(record[1], 6, 
                product.seller_ids[0].name.name if product.seller_ids else (
                    product.first_supplier_id.name or ''))
            if data.get('with_stock', False): 
                record[0].write(record[1], 7, product.mx_net_qty or '')
            record[1] += 1
                    
        return True
    # -------------------------------------------------------------------------
    #                             Wizard button event
    # -------------------------------------------------------------------------
    def print_report(self, cr, uid, ids, context=None):
        ''' Print report product
        '''
        if context is None: 
            context = {}

        wiz_proxy = self.browse(cr, uid, ids)[0]
            
        datas = {
            'wizard': True, # started from wizard
            'partner_id': wiz_proxy.partner_id.id,
            'partner_name': wiz_proxy.partner_id.name,
            'default_code': wiz_proxy.default_code or False,
            'categ_ids': [item.id for item in wiz_proxy.categ_ids],
            'categ_name': [item.name for item in wiz_proxy.categ_ids],
            'catalog_ids': [item.id for item in wiz_proxy.catalog_ids],
            'catalog_name': [item.name for item in wiz_proxy.catalog_ids],
            'status': wiz_proxy.status or False,
            'sortable': wiz_proxy.sortable or False,
            'mode': wiz_proxy.mode or False,
            'with_photo': wiz_proxy.with_photo,
            'with_stock': wiz_proxy.with_stock,
            }
        if wiz_proxy.statistic_category:
            datas['statistic_category'] = [
                item.strip() for item in (
                    wiz_proxy.statistic_category or '').split('|')]
        else:            
            datas['statistic_category'] = False
        
        if datas['mode'] == 'status':
            report_name = 'stock_status_report'
        elif datas['mode'] == 'simple':
            report_name = 'stock_status_simple_report'
        elif datas['mode'] == 'inventory':
            report_name = 'stock_status_inventory_report'
        else: # inventory_xls
            return self.extract_xls_inventory_file(
                cr, uid, ids, datas, context=context)
                       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            }

    _columns = { 
        'partner_id': fields.many2one('res.partner', 'Supplier', 
            domain=[
                ('supplier', '=', True), 
                ('is_company', '=', True),
                ('is_address', '=', False),
                ]), 
        'default_code': fields.char('Partial code', size=30), 
        'statistic_category': fields.char('Statistic category (separ.: |)', 
            size=50), 
        'categ_ids': fields.many2many(
            'product.category', 'product_category_status_rel', 
            'product_id', 'category_id', 
            'Category'),
        'catalog_ids': fields.many2many(
            'product.product.catalog', 'product_catalog_status_rel', 
            'product_id', 'catalog_id', 
            'Catalog'),
        'status': fields.selection([
            ('catalog', 'Catalog'),
            ('out', 'Out catalog'),
            ('stock', 'Stock'),
            ('obsolete', 'Obsolete'),
            ('sample', 'Sample'),
            ('todo', 'Todo'),
            ], 'Gamma'),
        'sortable': fields.boolean('Sortable'),
        'with_photo': fields.boolean('With photo'),
        'with_stock': fields.boolean('With stock'),
        'mode': fields.selection([
            ('status', 'Stock status'),
            ('simple', 'Simple status'),
            ('inventory', 'Inventory'),
            ('inventory_xls', 'Inventory XLS (exported file not report)'),
            ], 'Mode', required=True)
        }
        
    _defaults = {
        'with_photo': lambda *x: True,
        'mode': lambda *x: 'status',
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


