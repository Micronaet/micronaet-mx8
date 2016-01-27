#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import sys
import logging
import erppeek
import pickle
from datetime import datetime
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class Parser(report_sxw.rml_parse):
    counters = {}
    headers = {}
    
    def __init__(self, cr, uid, name, context):        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_object': self.get_object,
            'get_filter': self.get_filter
            
            # Utility:
            #'get_counter': self.get_counter,
            #'set_counter': self.set_counter,            
        })

    def get_filter(self, data):
        ''' Get filter selected
        '''
        data = data or {}
        return data.get('partner_name', '')
    
    def get_object(self, data):
        ''' Search all product elements
        '''
        def get_position_season(date):
            ''' Return position in array for correct season month:
            '''
            month = int(date[5:7])
            if month >= 9: # september = 0
                return month - 9
            # january = 4    
            return month + 3    
            
        # XXX DEBUG:
        debug_f = '/home/administrator/photo/xls/textilene_status.txt'
        debug_file = open(debug_f, 'w')

        # pool used:
        product_pool = self.pool.get('product.product')
        pick_pool = self.pool.get('stock.picking')
        sale_pool = self.pool.get('sale.order')
        bom_pool = self.pool.get('mrp.bom')
        
        product_ids = product_pool.search(self.cr, self.uid, [
            ('default_code', '=ilike', 'T%')])

        products = {}
        moved = [] # TODO used?
        for product in product_pool.browse(
                self.cr, self.uid, product_ids):
            # TODO check fabric with selection?
            
            products[product.default_code] = [
                # Reset counter for this product    
                product.inventory_start, # inv
                0.0, # tcar
                0.0, # tscar
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # MM
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # OC
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # OF
                #[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # SAL
                ]    
      
        # =====================================================================
        # Get parameters for search:
        # =====================================================================
        company_pool = self.pool.get('res.company')
        company_ids = company_pool.search(self.cr, self.uid, [])
        company_proxy = company_pool.browse(
            self.cr, self.uid, company_ids)[0]
            
        # Exclude partner list:
        exclude_partner_ids = []
        for item in company_proxy.stock_explude_partner_ids:
            exclude_partner_ids.append(item.id)
            
        # Append also this company partner (for inventory)    
        exclude_partner_ids.append(company_proxy.partner_id.id)
        
        # From date:
        # TODO limit orders:
        #from_date = datetime.now().strftime('%Y-01-01 00:00:00')    
        #to_date = datetime.now().strftime('%Y-12-31 23:59:59')    

        debug_file.write('\n\nExclude partner list:\n%s\n\n'% (
            exclude_partner_ids,)) # XXX DEBUG

        # Load bom first:
        boms = {} # key default code
        # TODO Change filter_
        bom_ids = bom_pool.search(self.cr, self.uid, [
            ('sql_import', '=', True)])
        for bom in bom_pool.browse(self.cr, self.uid, bom_ids):
            boms[bom.product_id.default_code] = bom # theres' default_code?

        # =====================================================================
        # UNLOAD PICKING (CUSTOMER ORDER PICK OUT)
        # =====================================================================
        # Better with OC?
        out_picking_type_ids = []
        for item in company_proxy.stock_report_unload_ids:
            out_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(self.cr, self.uid, [     
            # type pick filter   
            ('picking_type_id', 'in', out_picking_type_ids),
            # Partner exclusion
            # TODO('partner_id', 'not in', exclude_partner_ids), 
            # TODO check data date
            #('date', '>=', from_date), 
            #('date', '<=', to_date), 
            # TODO state filter
            ])
            
        #debug_file.write('\n\nUnload picking:\nPick;Origin;Code;Q.\n') # XXX DEBUG           
        for pick in pick_pool.browse(self.cr, self.uid, pick_ids):
            pos = get_position_season(pick.date) # cols  (min_date?)
            for line in pick.move_lines:
                product_code = line.product_id.default_code
                # ------------------
                # check direct sale:
                # ------------------
                if product_code in products:
                    products[default_code][3][pos] -= qty # MM block  
                    continue                  
                
                # ------------------
                # check bom product:
                # ------------------
                if product_code not in boms:
                    _logger.warning('No bom product')
                    continue
                
                bom = boms[product_code]
                # Loop on all elements:
                for fabric in bom.bom_line_ids:                                                  
                    default_code = fabric.product_id.default_code # XXX                
                    qty = line.product_uom_qty * fabric.product_qty
                
                    if default_code not in products:
                        _logger.error('No product/fabric in database')
                        continue                    
                    products[default_code][3][pos] -= qty # MM block
                    
                # TODO check state of line??
                    
                #debug_file.write('\n%s;%s;%s;%s' % (
                #    pick.name, pick.origin, default_code, 
                #    line.product_uom_qty)) # XXX DEBUG

        # =====================================================================
        # LOAD PICKING (CUSTOMER ORDER AND PICK IN )
        # =====================================================================
        in_picking_type_ids = []
        for item in company_proxy.stock_report_load_ids:
            in_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(self.cr, self.uid, [     
            # type pick filter   
            ('picking_type_id', 'in', in_picking_type_ids),            
            # Partner exclusion
            # TODO ('partner_id', 'not in', exclude_partner_ids),            
            # check data date
            #('date', '>=', from_date), # XXX correct for virtual?
            #('date', '<=', to_date),            
            # TODO state filter
            ])
        #debug_file.write('\n\nLoad picking:\nType;Pick;Origin;Code;Q.\n') # XXX DEBUG           
        for pick in pick_pool.browse(self.cr, self.uid, pick_ids):
            pos = get_position_season(pick.date) # for done cols  (min_date?)
            for line in pick.move_lines:
                default_code = line.product_id.default_code                              
                qty = line.product_uom_qty
                
                if default_code not in products:
                    _logger.warning('No product/fabric in database')
                    continue

                # Order not current delivered
                if line.state == 'assigned': # virtual
                    pos = get_position_season(line.date_expected)
                    products[default_code][5][pos] += qty # MM block
                    #debug_file.write('\nOF;%s;%s;%s;%s' % (
                    #    pick.name, pick.origin, default_code, 
                    #    line.product_uom_qty)) # XXX DEBUG

                # Order delivered so picking
                elif line.state == 'done':
                    products[default_code][3][pos] += qty # MM block
                    #debug_file.write('\nBF;%s;%s;%s;%s' % (
                    #    pick.name, pick.origin, default_code, 
                    #    line.product_uom_qty)) # XXX DEBUG
        
        # =====================================================================
        # UNLOAD ORDER (NON DELIVERED)
        # =====================================================================
        order_ids = sale_pool.search(self.cr, self.uid, [
            ('state', 'not in', ('cancel', 'send', 'draft')),
            ('pricelist_order', '=', False),
            # Also forecasted order
            # TODO filter date?            
            # TODO no partner exclusion
            ])
            
        for order in sale_pool.browse(self.cr, self.uid, order_ids):
            for line in order.order_line:
                # FC order no deadline (use date)
                pos = get_position_season(
                    line.date_deadline or order.date_order)
                    #datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)) 
                # TODO manage forecast order ...     

                product_code = line.product_id.default_code                              
                remain = line.product_uom_qty - line.delivered_qty
                if remain <=0: 
                    continue # delivered (so in pick out)
                # TODO check production?
                
                # Check for fabric order:
                if product_code in products: # sale fabric:
                    products[product_code][4][pos] += remain # OC block
                    continue
                
                if product_code not in boms:
                    _logger.warning('No bom product')
                    continue
                
                # Loop on all elements:
                for fabric in boms[product_code].bom_line_ids:                                                  
                    default_code = fabric.product_id.default_code # XXX                 
                    if default_code not in products:
                        _logger.error('No product/fabric in database')
                        continue
                    qty = remain * fabric.product_qty
                    products[default_code][4][pos] -= qty # OC block

                # debug_file.write('%s;%s;%s\n' % (
                #    line.order_id.name, default_code, remain)) # XXX DEBUG

        # Prepare data for report:     
        res = []       
        for key in sorted(products):
            res.append(products[key])
                
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
