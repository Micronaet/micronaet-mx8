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

# ---------------------------------------------------------------------
# Utility: 
# ---------------------------------------------------------------------
def write_header(current_WS, header, row=0, cell_format=False):
    ''' Write header in first line:            
    '''
    col = 0
    for title in header:
        if cell_format:
            current_WS.write(row, col, title, cell_format)
        else:    
            current_WS.write(row, col, title)
        col += 1
    return     

class StockStatusPrintImageReportWizard(orm.TransientModel):
    ''' Wizard for print stock status
    '''
    _name = 'stock.status.print.image.report.wizard'

    def extract_xls_check_inventory_file(self, cr, uid, ids, data=None,
            context=None):
        ''' Extract inventory as XLS extrenal files every category in different
            page
            TODO Correct and write better!!!
        '''
        # ---------------------------------------------------------------------
        #                        XLS log export:        
        # ---------------------------------------------------------------------
        filename = '/home/administrator/photo/output/post_inventory_table.xlsx'
        _logger.info('Extract: %s' % filename)
        WB = xlsxwriter.Workbook(filename)

        # ---------------------------------------------------------------------
        # Create work sheet:
        # ---------------------------------------------------------------------
        header = ['DB', 'CODICE', 'DESCRIZIONE', 'UM', 
            'CAT. STAT.', 'CATEGORIA', 'FORNITORE', 'INV', 'INV. DELTA', 'MRP', 
            'CATEGORIA INVENTARIO',
            'INVENTARIO 31/12', 'INVENTARIO 1/1', 'COSTO', 'MODIFICA', 
            'DATA QUOTAZIONE',
            ]
        
        # Create element for empty category:
        WS = WB.add_worksheet('Controlli inventario')
        counter = 0
        write_header(WS, header)

        # ---------------------------------------------------------------------
        # Prepare price last buy check
        # ---------------------------------------------------------------------
        price_pool = self.pool.get('pricelist.partnerinfo')
        price_ids = price_pool.search(cr, uid, [], 
            order='write_date DESC', context=context)

        price_db = {}
        for price in price_pool.browse(cr, uid, price_ids, context=context):
            product = price.product_id #suppinfo_id.name 
            # price.suppinfo_id.product_tmpl_id.id
            if product.id in price_db:
                continue
            price_db[product.id] = (
                price.price, price.write_date, price.date_quotation)
            
        # ---------------------------------------------------------------------
        # Prepare BOM check
        # ---------------------------------------------------------------------
        line_pool = self.pool.get('mrp.bom.line')
        line_ids = line_pool.search(cr, uid, [
            ('bom_id.bom_category', 'in', ('parent', 'dynamic', 'half')),
            ], context=context)

        in_bom_ids = [item.product_id.id for item in line_pool.browse(
            cr, uid, line_ids, context=context)]

        # TODO remove after print:
        with_parent_bom = False
        linked_bom = {}
        if with_parent_bom:         
            linked_bom_ids = line_pool.search(cr, uid, [
                ('bom_id.bom_category', '=', 'parent'),
                ], context=context)
            for line in line_pool.browse(cr, uid, linked_bom_ids, 
                    context=context):
                linked_bom[
                    line.product_id.id] = line.bom_id.product_id.default_code
                
        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        counter = 0
        for product in self.pool.get(
                'product.product').stock_status_report_get_object(
                    cr, uid, data=data, context=context):                    
            counter += 1

            price_item = price_db.get(product.id, ('', '', ''))
            
            # Write data in correct WS:
            WS.write(counter, 0, 'X' if product.id in in_bom_ids else '') # A
            WS.write(counter, 1, product.default_code) # B
            WS.write(counter, 2, product.name) # C
            WS.write(counter, 3, product.uom_id.name or '') # D
            WS.write(counter, 4, product.statistic_category or '') # E
            WS.write(counter, 5, product.categ_id.name or '') # F
            WS.write(counter, 6,
                product.seller_ids[0].name.name if product.seller_ids else (
                    product.first_supplier_id.name or '')) # G
            WS.write(counter, 7, product.inventory_start or '') # H
            WS.write(counter, 8, product.inventory_delta or '') # I
            WS.write(counter, 9, product.mx_mrp_out or '') # J
            WS.write(counter, 10, product.inventory_category_id.name) # K
            WS.write(counter, 11, product.mx_history_net_qty or '') # L          
            WS.write(counter, 12, product.mx_start_qty or '') # M      
            WS.write(counter, 13, price_item[0]) # N
            WS.write(counter, 14, price_item[1]) # O
            WS.write(counter, 15, price_item[2]) # P
        return True
        
    def extract_stock_status_xls_inventory_file(self, cr, uid, ids, data=None,
            context=None):
        ''' Extract inventory as XLS extrenal files every category in different
            page
        '''    
        product_pool = self.pool.get('product.product')
        
        # ---------------------------------------------------------------------
        #                        XLS log export:        
        # ---------------------------------------------------------------------
        filename = '/tmp/inventory_status.xlsx'
        WB = xlsxwriter.Workbook(filename)
        WS = WB.add_worksheet(_('Inventario'))

        # ---------------------------------------------------------------------
        # Format:
        # ---------------------------------------------------------------------
        format_title = WB.add_format({
            'bold': True, 
            'font_color': 'black',
            'font_name': 'Verdana',
            'font_size': 9,
            #'align': 'center',
            #'valign': 'vcenter',
            #'bg_color': 'gray',
            #'border': 1,
            #'text_wrap': True,
            })
        format_header = WB.add_format({
            'bold': True, 
            'font_color': 'black',
            'font_name': 'Verdana',
            'font_size': 9,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'gray',
            'border': 1,
            'text_wrap': True,
            })
        format_text = WB.add_format({
            'font_name': 'Courier 10 Pitch',
            'font_size': 8,
            #'align': 'right',
            #'bg_color': 'c1e7b3',
            'border': 1,
            #'num_format': '0.00',
            })        
        
        # ---------------------------------------------------------------------
        # Setup dimension:
        # ---------------------------------------------------------------------
        # Columns:
        WS.set_column('A:A', 15)
        WS.set_column('B:B', 40)
        WS.set_column('C:C', 5)
        WS.set_column('D:D', 8)
        WS.set_column('E:E', 10)
        WS.set_column('F:F', 35)
        WS.set_column('G:J', 16)
        WS.set_column('K:M', 8)
        WS.set_column('N:N', 5)
        WS.set_column('O:Q', 8)

        # Rows:
        WS.set_row(3, 25)
        
        # ---------------------------------------------------------------------
        # Create work sheet:
        # ---------------------------------------------------------------------
        # Title:
        header = [
            'CODICE', 'DESCRIZIONE', 'UM', 'CAT. STAT.', 
            'CATEGORIA', 'FORNITORE', 'RIF. FORNITORE', 'ULTIMO ACQ.', 
            'COSTO FOM FORN.', 'ESISTENZA', 'COSTO INV.', 'DAZI', 
            'TRASPORTO', 'USD', 'COSTO EUR', 'DAZIO EUR', 'COSTO FIN. EUR',
            ]
        
        # Write 3 line of header:
        write_header(
            WS, ['', 'RACCOLTA DATI PER INVENTARIO', ], 0, format_title)
        write_header(WS, [
            _('Filtro'), 
            product_pool.mx_stock_status_get_filter(data),
            product_pool.get_purchase_last_date(False, True),
            ], 1, format_title)        
        write_header(WS, header, 3, format_header)
            
        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        row = 3
        for o in product_pool.stock_status_report_get_object(
                    cr, uid, data=data, context=context):                    
            row += 1        
            
            # Calculate:
            duty = product_pool.get_duty_this_product_rate(o) # L
            cost_fob = o.standard_price # I
            usd = o.inventory_cost_exchange # N
            transport = o.inventory_cost_transport # M
            
            if usd:
                cost_eur = cost_fob / usd # O
                cost_duty_eur = cost_fob * duty / 100.0 / usd # P
                cost_end_eur = cost_eur + cost_duty_eur + transport # Q
            else:
                cost_eur = 'ERR' # O
                cost_duty_eur = 'ERR' # P 
                cost_end_eur = 'ERR' # Q
                
                
            if o.seller_ids:
                supplier = \
                    o.first_supplier_id.name or o.seller_ids[0].name.name # F
                supplier_ref = '%s %s' % (
                    o.seller_ids[0].product_code or '',
                    o.seller_ids[0].product_name or '',
                    ) # G
            else:
                supplier = o.first_supplier_id.name or '?' # F
                supplier_ref = '?'
            
            # Write data in correct WS:
            WS.write(row, 0, o.default_code or '????', format_text) # A
            WS.write(row, 1, o.name or '', format_text) # B
            WS.write(row, 2, o.uom_id.name or '', format_text) # C
            WS.write(row, 3, o.statistic_category or '', format_text) # D
            WS.write(row, 4, o.categ_id.name or '', format_text) # E 
            WS.write(row, 5, supplier, format_text) # F
            WS.write(row, 6, supplier_ref, format_text) # G
            WS.write(row, 7, product_pool.get_purchase_last_date(
                cr, uid, o.default_code, context=context), format_text) # H
            WS.write(row, 8, cost_fob, format_text) # I
            WS.write(row, 9, 
                o.mx_net_qty if data.get('with_stock', False) else '/', 
                format_text) # J
            WS.write(row, 10, o.inventory_cost_no_move, format_text) # K
            WS.write(row, 11, duty, format_text) # L
            WS.write(row, 12, transport, format_text) # M
            WS.write(row, 13, usd, format_text) # N
            WS.write(row, 14, cost_eur, format_text) # O
            WS.write(row, 15, cost_duty_eur, format_text) # P            
            WS.write(row, 16, cost_end_eur, format_text) # Q
        WB.close()    
            
        # ---------------------------------------------------------------------
        # Generate attachment for return file:
        # ---------------------------------------------------------------------        
        attachment_pool = self.pool.get('ir.attachment')
        b64 = open(filename, 'rb').read().encode('base64')
        attachment_id = attachment_pool.create(cr, uid, {
            'name': 'Temp report',
            'datas_fname': 'stato_inventario.xlsx',
            'type': 'binary',
            'datas': b64,
            'partner_id': 1,
            'res_model': 'res.partner',
            'res_id': 1,
            }, context=context)        
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/saveas?model=ir.attachment&field=datas&'
                'filename_field=datas_fname&id=%s' % attachment_id,
            'target': 'self',
            }

    def extract_xls_inventory_file(self, cr, uid, ids, data=None,
            context=None):
        ''' Extract inventory as XLS extrenal files every category in different
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
        filename = '/home/administrator/photo/output/inventory_table.xlsx'
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
            'CATEGORIA', 'FORNITORE', 'INV', 'INV. DELTA', 'MRP', 'ESISTENZA']
        
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
        # TODO check if there's production mode:
        line_pool = self.pool.get('mrp.bom.line')
        line_ids = line_pool.search(cr, uid, [
            ('bom_id.bom_category', 'in', ('parent', 'dynamic', 'half')),
            ], context=context)

        in_bom_ids = [item.product_id.id for item in line_pool.browse(
            cr, uid, line_ids, context=context)]

        # TODO remove after print:
        with_parent_bom = False
        linked_bom = {}
        if with_parent_bom:         
            linked_bom_ids = line_pool.search(cr, uid, [
                ('bom_id.bom_category', '=', 'parent'),
                ], context=context)
            for line in line_pool.browse(cr, uid, linked_bom_ids, 
                    context=context):
                linked_bom[
                    line.product_id.id] = line.bom_id.product_id.default_code
                
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
                net_qty = product.mx_net_qty - product.mx_mrp_out
                record[0].write(record[1], 7, product.inventory_start or '')
                record[0].write(record[1], 8, product.inventory_delta or '')
                record[0].write(record[1], 9, product.mx_mrp_out or '')
                record[0].write(record[1], 10, net_qty or '')
                
            # TODO remove after print:    
            if with_parent_bom:         
                record[0].write(record[1], 11, linked_bom.get(product.id, ''))
                
            record[1] += 1                    
        return True

    # -------------------------------------------------------------------------
    #                             Wizard button event
    # -------------------------------------------------------------------------
    def get_data_dict(self, wiz_proxy):
        ''' Utility for create data dict in report actions
        '''
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
            'inventory_category_id': wiz_proxy.inventory_category_id.id,
            }

        if wiz_proxy.statistic_category:
            datas['statistic_category'] = [
                item.strip() for item in (
                    wiz_proxy.statistic_category or '').split('|')]
        else:            
            datas['statistic_category'] = False
        return datas    
        
    def print_report(self, cr, uid, ids, context=None):
        ''' Print report product
        '''
        if context is None: 
            context = {}

        wiz_proxy = self.browse(cr, uid, ids)[0]            
        datas = self.get_data_dict(wiz_proxy)
        
        if datas['mode'] == 'status':
            report_name = 'stock_status_report'
        elif datas['mode'] == 'simple':
            report_name = 'stock_status_simple_report'
        elif datas['mode'] == 'inventory':
            # XXX Migrate in Excel:
            #report_name = 'stock_status_inventory_report'
            return self.extract_stock_status_xls_inventory_file(
                cr, uid, ids, datas, context=context)
            
        elif datas['mode'] == 'inventory_xls':
            return self.extract_xls_inventory_file(
                cr, uid, ids, datas, context=context)
        elif datas['mode'] == 'inventory_check_xls':
            return self.extract_xls_check_inventory_file(
                cr, uid, ids, datas, context=context)
        #elif datas['mode'] == 'inventory_web':
        #    return self.extract_web_inventory_file(
        #        cr, uid, ids, datas, context=context)
        else:
            raise osv.except_osv(
                _('No type'), 
                _('Check type setup (not present)'),
                )        
                       
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
        'inventory_category_id': fields.many2one(
            'product.product.inventory.category', 'Inventory category'),    
        'status': fields.selection([
            ('catalog', 'Catalog'),
            ('out', 'Out catalog'),
            ('stock', 'Stock'),
            ('obsolete', 'Obsolete'),
            ('sample', 'Sample'),
            ('promo', 'Promo'),
            ('parent', 'Padre'),
            ('todo', 'Todo'),
            ], 'Gamma'),
        'sortable': fields.boolean('Sortable'),
        'with_photo': fields.boolean('With photo'),
        'with_stock': fields.boolean('With stock'),
        'mode': fields.selection([
            ('status', 'Stock status'),
            ('simple', 'Simple status'),
            ('inventory', 'Inventory'),
            ('inventory_xls', 'Inventory XLS (exported not report)'),
            ('inventory_check_xls', 'Inventory check XLS (exported not report)'),
            ], 'Mode', required=True)
        }
        
    _defaults = {
        'with_photo': lambda *x: True,
        'mode': lambda *x: 'status',
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


