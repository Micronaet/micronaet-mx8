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
            'get_jumped': self.get_jumped,
            'get_filter': self.get_filter,
            'get_date': self.get_date,
            })

    def get_jumped(self, ):
        ''' Get filter selected
        '''
        return self.jumped

    def get_date(self, ):
        ''' Get filter selected
        '''
        return datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

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
            if not date:
                _logger.error('Date not found')
                return False
            month = int(date[5:7])
            if month >= 9: # september = 0
                return month - 9
            # january = 4    
            return month + 3    
            
        # XXX DEBUG:
        debug_f = '/home/administrator/photo/xls/textilene_status.txt'
        debug_f_mm = '/home/administrator/photo/xls/textilene_mm.csv'
        debug_file = open(debug_f, 'w')
        debug_mm = open(debug_f_mm, 'w')

        # pool used:
        product_pool = self.pool.get('product.product')
        pick_pool = self.pool.get('stock.picking')
        sale_pool = self.pool.get('sale.order')
        bom_pool = self.pool.get('mrp.bom')
        
        product_ids = product_pool.search(self.cr, self.uid, [
            ('default_code', '=ilike', 'T%'),
            ('not_in_report', '=', False),
            ])

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
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # SAL
                product,
                ]

        debug_file.write('\n\nProduct fabric selected:\n%s\n\n'% (
            products.keys())) # XXX DEBUG

        # =====================================================================
        # Get parameters for search:
        # =====================================================================
        company_pool = self.pool.get('res.company')
        company_ids = company_pool.search(self.cr, self.uid, [])
        company_proxy = company_pool.browse(
            self.cr, self.uid, company_ids)[0]
            
        # Exclude partner list:
        exclude_partner_ids = []
        #for item in company_proxy.stock_explude_partner_ids:
        #    exclude_partner_ids.append(item.id)
            
        # Append also this company partner (for inventory)    
        exclude_partner_ids.append(company_proxy.partner_id.id)
        
        # From date:
        # Period range for documents
        month = datetime.now().month
        year = datetime.now().year
        if month >= 9:
            period_from = '%s-09-01' % year
            period_to = '%s-08-31' % (year + 1)
        else:
            period_from = '%s-09-01' % (year - 1)
            period_to = '%s-08-31' % year
            
        #from_date = datetime.now().strftime('%Y-01-01 00:00:00')    
        #to_date = datetime.now().strftime('%Y-12-31 23:59:59')    

        debug_file.write('\n\nExclude partner list:\n%s\n\n'% (
            exclude_partner_ids,)) # XXX DEBUG

        # Load bom first:
        boms = {} # key default code
        # TODO Change filter_
        debug_file.write('\n\nBOM list\n') # XXX DEBUG

        bom_ids = bom_pool.search(self.cr, self.uid, [
            ('sql_import', '=', True)])
        for bom in bom_pool.browse(self.cr, self.uid, bom_ids):
            boms[bom.product_id.default_code] = bom # theres' default_code?
            debug_file.write('\nProduct: %s [%s]' % (
                 bom.product_id.default_code,
                 len(bom.bom_line_ids),
                 )) # XXX DEBUG

        # XXX debug
        debug_mm.write(
            'Block|State|Doc.|Origin|Date|Pos.|Prod.|MP|Calc.|MM|OC|OF|Note\n')
        mask = '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n'    
        # =====================================================================
        # UNLOAD PICKING (CUSTOMER ORDER PICK OUT)
        # =====================================================================
        block = 'BC PICK OUT'
            
        # Better with OC?
        out_picking_type_ids = []
        for item in company_proxy.stock_report_unload_ids:
            out_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(self.cr, self.uid, [     
            # type pick filter   
            ('picking_type_id', 'in', out_picking_type_ids),
            # Partner exclusion
            ('partner_id', 'not in', exclude_partner_ids), # only company
            
            # TODO check data date
            #('date', '>=', from_date), 
            #('date', '<=', to_date), 
            # TODO state filter
            ])
            
        for pick in pick_pool.browse(self.cr, self.uid, pick_ids):
            pos = get_position_season(pick.date) # cols  (min_date?)
            # TODO no check for period range
            for line in pick.move_lines:                
                product_code = line.product_id.default_code
                if line.state != 'done':
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        pick.name,
                        pick.origin,
                        pick.date,
                        pos,
                        product_code,                                
                        '',
                        '',
                        0,
                        0,
                        0,
                        'State not in done (jumped)',
                        ))
                    continue    
                    
                # ------------------
                # check direct sale:
                # ------------------
                if product_code in products: # Fabric:
                    qty = line.product_uom_qty # for direct sale            
                    products[product_code][3][pos] -= qty # MM block  
                    products[product_code][2] = qty # TSCAR
                    debug_mm.write(mask % (
                        block,
                        'USED',
                        pick.name,
                        pick.origin,
                        pick.date,
                        pos,
                        '',
                        product_code, # Prod is MP
                        '',
                        ('%s' % -qty).replace('.', ','), # MM
                        0,
                        0,
                        'Direct sale of fabric (ADD IN TSCAR)',
                        ))
                    continue    
                
                # ------------------
                # check bom product:
                # ------------------
                if product_code not in boms: # Product
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        pick.name,
                        pick.origin,
                        pick.date,
                        pos,
                        product_code,                                
                        '',
                        '',
                        0,
                        0,
                        0,
                        'Warn. product not in BOM',
                        ))                      
                    continue
                
                bom = boms[product_code]
                # Loop on all elements:
                
                bom_product = []
                for fabric in bom.bom_line_ids:                                                  
                    default_code = fabric.product_id.default_code                
                    if default_code in bom_product:
                        _logger.error(
                            'BOM double problem: %s' % product_code)
                        # TODO remove ID?
                        continue    
                    bom_product.append(default_code)
                    
                    if default_code not in products:
                        debug_mm.write(mask % (
                            block,
                            'NOT USED',
                            pick.name,
                            pick.origin,
                            pick.date,
                            pos,
                            product_code,                                
                            default_code,
                            '',
                            0,
                            0,
                            0,
                            'Warn. fabric not in BOM',
                            ))                      
                        continue
                                        
                    qty = line.product_uom_qty * fabric.product_qty
                    products[default_code][3][pos] -= qty # MM block
                    products[default_code][2] = qty # TSCAR

                    debug_mm.write(mask % (
                        block,
                        'USED',
                        pick.name,
                        pick.origin,
                        pick.date,
                        pos,
                        product_code,                                
                        default_code,
                        '%s X %s' % (
                            line.product_uom_qty,
                            fabric.product_qty,
                            ),
                        ('%s' % -qty).replace('.', ','),
                        0,
                        0,
                        'BOM component (ADD IN TSCAR)',
                        ))                      
                    continue

        # =====================================================================
        # LOAD PICKING (CUSTOMER ORDER AND PICK IN )
        # =====================================================================
        block = 'OF and BF'
        in_picking_type_ids = []
        for item in company_proxy.stock_report_load_ids:
            in_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(self.cr, self.uid, [     
            # type pick filter   
            ('picking_type_id', 'in', in_picking_type_ids),            
            # Partner exclusion
            ('partner_id', 'not in', exclude_partner_ids),            
            # check data date
            #('date', '>=', from_date), # XXX correct for virtual?
            #('date', '<=', to_date),            
            # TODO state filter
            ])
            
        for pick in pick_pool.browse(self.cr, self.uid, pick_ids):
            pos = get_position_season(pick.date) # for done cols  (min_date?)
            for line in pick.move_lines:
                default_code = line.product_id.default_code                              
                qty = line.product_uom_qty
                
                if default_code not in products:
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        pick.name,
                        pick.origin,
                        pick.date,
                        pos,
                        '', # product_code
                        default_code,
                        '',
                        0,
                        0,
                        0,
                        'OF / BF Warn. Code not in fabric',
                        ))                      
                    continue

                # Order not current delivered
                # -------------------------------------------------------------
                #          OF document
                # -------------------------------------------------------------
                if line.state == 'assigned': # virtual
                    # USE deadline data:
                    # Before check date:
                    if line.date_expected > period_to: # over range
                        debug_mm.write(mask % (
                            block,
                            'NOT USED',
                            pick.name,
                            pick.origin,
                            line.date_expected,
                            '', # POS
                            '', # product_code                                
                            default_code,
                            '',
                            0,
                            0,
                            0,
                            'OF date expected over range!!: Q.: %s' % qty,
                            ))                      
                        continue

                    if line.date_expected < period_from: # under range
                        debug_mm.write(mask % (
                            block,
                            'NOT USED',
                            pick.name,
                            pick.origin,
                            line.date_expected,
                            '', # POS
                            '', # product_code                                
                            default_code,
                            '',
                            0,
                            0,
                            0,
                            'OF date expected under range!!: Q.: %s' % qty,
                            ))                      
                        continue

                    pos = get_position_season(line.date_expected)
                    products[default_code][5][pos] += qty # OF block
                    debug_mm.write(mask % (
                        block,
                        'USED',
                        pick.name,
                        pick.origin,
                        line.date_expected,
                        pos,
                        '', # product_code                                
                        default_code,
                        '',
                        0,
                        0,
                        ('%s' % qty).replace('.', ','),
                        'OF',
                        ))                      
                    continue

                # Order delivered so picking
                # -------------------------------------------------------------
                #          BF document
                # -------------------------------------------------------------
                elif line.state == 'done':
                    date = pick.date_done or pick.min_date or pick.date
                    pos = get_position_season(date)
                
                    # USE order data:
                    if date > period_to: # over range
                        debug_mm.write(mask % (
                            block,
                            'NOT USED',
                            pick.name,
                            pick.origin,
                            date,
                            pos,
                            '', # product_code                                
                            default_code,
                            '',
                            0,
                            0,
                            0,
                            'BF date doc over range!!: Q.: %s' % qty,
                            ))                      
                        continue

                    if date < period_from: # under range
                        debug_mm.write(mask % (
                            block,
                            'NOT USED',
                            pick.name,
                            pick.origin,
                            date,
                            pos,
                            '', # product_code                                
                            default_code,
                            '',
                            0,
                            0,
                            0,
                            'BF date doc under range!!: Q.: %s' % qty,
                            ))                      
                        continue
                    
                    products[default_code][3][pos] += qty # MM block
                    products[default_code][1] += qty # TCAR                    
                    debug_mm.write(mask % (
                        block,
                        'USED',
                        pick.name,
                        pick.origin,
                        date,
                        pos,
                        '', # product_code                                
                        default_code,
                        '',
                        ('%s' % qty).replace('.', ','), # +MM
                        0,
                        0,
                        'BF ADD IN TCAR',
                        ))                      
                    continue
        
        # =====================================================================
        # UNLOAD ORDER (NON DELIVERED)
        # =====================================================================
        block = 'OC (not delivered)'
        order_ids = sale_pool.search(self.cr, self.uid, [
            ('state', 'not in', ('cancel', 'send', 'draft')),
            ('pricelist_order', '=', False),
            ('partner_id', 'not in', exclude_partner_ids),            
            # Also forecasted order
            # TODO filter date?            
            # TODO no partner exclusion
            ])
            
        for order in sale_pool.browse(self.cr, self.uid, order_ids):
            for line in order.order_line:
                product_code = line.product_id.default_code                              

                # FC order no deadline (use date)
                date = line.date_deadline or order.date_order
                pos = get_position_season(date)
                #datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)) 
                    
                # TODO manage forecast order ...     
                remain = line.product_uom_qty - line.delivered_qty
                if remain <= 0:
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        order.name,
                        '',
                        date,
                        pos,
                        product_code,
                        '', # MP
                        '',
                        0, # +MM
                        0,
                        0,
                        'ALL DELIVERED',
                        ))                      
                    continue
            
                # USE order data:
                if date > period_to: # over range
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        order.name,
                        '',
                        date,
                        pos,
                        product_code,
                        '', # MP
                        '',
                        0, # +MM
                        0,
                        0,
                        'OVER RANGE, qty: %s' % remain,
                        ))                      
                    continue

                if date < period_from: # under range
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        order.name,
                        '',
                        date,
                        pos,
                        product_code,
                        '', # MP
                        '',
                        0, # +MM
                        0,
                        0,
                        'UNDER RANGE, qty: %s' % remain,
                        ))                      
                    continue

                # Check for fabric order:
                if product_code in products: # OC out fabric (no prod.):
                    products[product_code][4][pos] -= remain # OC block
                    debug_mm.write(mask % (
                        block,
                        'USED',
                        order.name,
                        '',
                        date,
                        pos,
                        '', #product_code
                        product_code, # MP
                        '',
                        0, # +MM
                        ('%s' % remain).replace('.', ','), # -OC
                        0,
                        'FABRIC DIRECT',
                        ))                      
                    continue
                
                if product_code not in boms:
                    debug_mm.write(mask % (
                        block,
                        'NOT USED',
                        order.name,
                        '',
                        date,
                        pos,
                        product_code,
                        '', #MP
                        '',
                        0, # +MM
                        0, # -OC
                        0,
                        'PRODUCT WITHOUT BOM, Q.: %s' % qty,
                        ))                      
                    continue
                
                # Check ordered    
                if line.product_uom_maked_sync_qty: # Remain order to produce:
                    move_qty = line.product_uom_qty - \
                        line.product_uom_maked_sync_qty
                    note = 'Remain order with production (OC - B)'
                else: # No production: # Remain ordered to delivery:
                    move_qty = line.product_uom_qty - \
                        line.delivered_qty    
                    note = 'Remain order without production (OC - Delivered)'
                    
                # same as previous    
                #date = line.date_deadline or order.date_order
                #pos = get_position_season(date) 
                if move_qty: # Remain order >> =C
                    # Loop on all elements:
                    i = 0        
                    bom_product = []            
                    for fabric in boms[product_code].bom_line_ids:                                                  
                        i += 1
                        default_code = fabric.product_id.default_code # XXX 

                        # Check bom problem:                
                        if default_code in bom_product:
                            _logger.error(
                                'BOM double problem: %s' % product_code)
                            # TODO remove ID?
                            continue    
                        bom_product.append(default_code)
                            
                        if default_code not in products:
                            debug_mm.write(mask % (
                                block,
                                'NOT USED',
                                order.name,
                                '',
                                date,
                                pos,
                                product_code,
                                default_code, # MP
                                '',
                                0, # +MM
                                0, # -OC
                                0,
                                'ERROR FABRIC NOT IN DATABASE!',
                                ))                      
                            continue
                        
                        qty = move_qty * fabric.product_qty
                        products[default_code][4][pos] -= qty # OC block # XXX was -
                        
                        debug_mm.write(mask % (
                            block,
                            'USED',
                            order.name,
                            '',
                            date,
                            pos,
                            product_code,
                            default_code,
                            '%s x %s' % (
                                move_qty, 
                                fabric.product_qty,
                                ),
                            0, # +MM
                            ('%s' % qty).replace('.', ','), # +OC
                            0,
                            '[BOM # %s] REMAIN OC [%s]' % ( 
                                i,
                                note,
                                )
                            ))                      
                        continue

                # Check production: >> MM
                if line.product_uom_maked_sync_qty:
                    move_qty = line.product_uom_maked_sync_qty - \
                        line.delivered_qty                  
                    # TODO add other date when unlink order      
                    # TODO log this change!!
                    date = line.mrp_id.date_planned or datetime.now().strftime(
                        DEFAULT_SERVER_DATE_FORMAT)
                    pos = get_position_season(date)
                
                    # Loop on all elements:
                    i = 0
                    
                    bom_product = []
                    for fabric in boms[product_code].bom_line_ids:                                                  
                        i += 1
                        default_code = fabric.product_id.default_code # XXX                 
                        if default_code in bom_product:
                            _logger.error(
                                'BOM double problem: %s' % product_code)
                            # TODO remove ID?
                            continue    
                        bom_product.append(default_code)
                            
                        if default_code not in products:
                            debug_mm.write(mask % (
                                block,
                                'NOT USED',
                                order.name,
                                '',
                                date,
                                pos,
                                product_code,
                                default_code, # MP
                                '',
                                0, # +MM
                                0, # -OC
                                0,
                                'ERROR FABRIC NOT IN DATABASE (REMAIN B)!',
                                ))                      
                            continue
                        
                        qty = move_qty * fabric.product_qty
                        products[default_code][3][pos] -= qty # - MM block
                        products[default_code][2] -= qty # TSCAR

                        debug_mm.write(mask % (
                            block,
                            'USED',
                            order.name,
                            '',
                            date,
                            pos,
                            product_code,
                            default_code,
                            '%s x %s' % (
                                move_qty, 
                                fabric.product_qty,
                                ),
                            ('%s' % -qty).replace('.', ','), # -MM
                            0, # +OC
                            0,
                            '[BOM #: %s] PROD TO DELIV (B-DEL.) TSCAR %s' % (
                                i,
                                note,
                                )
                            ))                      
                        continue

        # Prepare data for report:     
        res = []
        self.jumped = []
        for key in sorted(products, key=lambda products: '%s%s%s' % (
                products[0:3] or '   ',
                products[6:12] or '      ',
                products[3:6] or '   ',
                )):
            current = products[key] # readability:
            total = 0.0 # INV 0.0
            
            # NOTE: INV now is 31/12 next put Sept.
            inv_pos = 3 # December
            jumped = False
            for i in range(0, 12):
                #if i == inv_pos:
                #    current[3][i] += round(current[0], 0) # add inv.
                current[3][i] = int(round(current[3][i], 0))
                current[4][i] = int(round(current[4][i], 0))
                current[5][i] = int(round(current[5][i], 0))
                
                if not(any(current[3]) or any(current[4]) or \
                        any(current[5]) or current[0]> 0.0):
                    #_logger.warning('Jumped: %s %s %s' % current
                    self.jumped.append(current[7]) # product proxy
                    jumped = True
                    continue    
                
                if i == inv_pos:
                    total += round(current[0], 0) # add inv.
                total += round(
                    current[3][i] + current[4][i] + current[5][i], 0)
                current[6][i] = int(total)

            # Append progress totals:
            if not jumped:
                res.append(current)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
