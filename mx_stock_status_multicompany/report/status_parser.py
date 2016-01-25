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
from datetime import datetime
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.tools.translate import _

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
        # pool used:
        product_pool = self.pool.get('product.product')
        supplier_pool = self.pool.get('product.supplierinfo')
        pick_pool = self.pool.get('stock.picking')
        sale_pool = self.pool.get('sale.order') # XXX maybe not used 
        sol_pool = self.pool.get('sale.order.line') # XXX maybe not used 
        # procurements in stock.picking
        
        # ---------------------------------------------------------------------
        # Search partner in supplier info:
        # ---------------------------------------------------------------------
        partner_id = data.get('partner_id', False)        
        supplierinfo_ids = supplier_pool.search(self.cr, self.uid, [
            ('name', '=', partner_id)])           

        # ---------------------------------------------------------------------
        # Get template product supplier by partner
        # ---------------------------------------------------------------------
        # XXX DEBUG:
        debug_file = open('/home/administrator/photo/xls/status.txt', 'w')

        company_proxy = False
        product_tmpl_ids = []
        for supplier in supplier_pool.browse(
                self.cr, self.uid, supplierinfo_ids):
            if not company_proxy:
                company_proxy = supplier.name.company_id
            product_tmpl_ids.append(supplier.product_tmpl_id.id)        
        
        if not product_tmpl_ids:
            raise osv.except_osv(
                _('Report error'),
                _('No data for this partner',
                ))

        debug_file.write('\nTemplate selected:\n') # XXX DEBUG
        debug_file.write('%s' % (product_tmpl_ids)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Get product form template:
        # ---------------------------------------------------------------------        
        product_ids = product_pool.search(self.cr, self.uid, [
            ('product_tmpl_id', 'in', product_tmpl_ids)])
        products = {}
        product_mask = company_proxy.product_mask or ''
        products_code = [] # For search in other database

        for product in product_pool.browse(self.cr, self.uid, product_ids):                
            default_code = product.default_code
            products_code.append(product_mask % default_code)
            if default_code in products:
                _logger.error('More than one default_code %s' % default_code)                
            products[default_code] = product

        debug_file.write('\n\nProduct code searched in other DB\n') # XXX DEBUG
        debug_file.write('%s' % (products_code, )) # XXX DEBUG
        debug_file.write('\n\nProduct selected:\n') # XXX DEBUG
        debug_file.write('%s' % (product_ids,)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Parameter for filters:
        # ---------------------------------------------------------------------
        # Exclunde partner list:
        exclude_partner_ids = []
        for item in company_proxy.stock_explude_partner_ids:
            exclude_partner_ids.append(item.id)
        # Append also this company partner (for inventory)    
        exclude_partner_ids.append(company_proxy.partner_id.id)
        
        # From date:
        from_date = datetime.now().strftime('%Y-01-01 00:00:00')    
        to_date = datetime.now().strftime('%Y-12-31 23:59:59')    

        debug_file.write('\n\nExclude partner list:') # XXX DEBUG
        debug_file.write('%s' % (exclude_partner_ids,)) # XXX DEBUG
        # ---------------------------------------------------------------------
        # Get unload picking
        # ---------------------------------------------------------------------
        unloads = {}
        out_picking_type_ids = []
        for item in company_proxy.stock_report_unload_ids:
            out_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(self.cr, self.uid, [     
            # type pick filter   
            ('picking_type_id', 'in', out_picking_type_ids), 
            
            # Partner exclusion
            ('partner_id', 'not in', exclude_partner_ids), 
            
            # TODO check data date
            ('date', '>=', from_date), 
            ('date', '<=', to_date), 
            
            # TODO state filter
            ])

        debug_file.write('\n\nUnload picking:\n') # XXX  DEBUG           
        for pick in pick_pool.browse(self.cr, self.uid, pick_ids):
            debug_file.write('\nPick: %s' % pick.name) # XXX DEBUG
            for line in pick.move_lines:
                if line.product_id.id in product_ids: # only supplier prod.
                    # TODO check state of line??
                    default_code = line.product_id.default_code
                    if default_code not in unloads:
                        unloads[default_code] = line.product_uom_qty
                    else:    
                        unloads[default_code] += line.product_uom_qty
                debug_file.write('Prod.: %s [%s]\n' % (
                    default_code, line.product_uom_qty)) # XXX DEBUG

        # ---------------------------------------------------------------------
        # Get unload picking
        # ---------------------------------------------------------------------
        loads = {}
        virtual_loads = {}
        in_picking_type_ids = []
        for item in company_proxy.stock_report_load_ids:
            in_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(self.cr, self.uid, [     
            # type pick filter   
            ('picking_type_id', 'in', in_picking_type_ids), 
            
            # Partner exclusion
            ('partner_id', 'not in', exclude_partner_ids), 
            
            # check data date
            ('date', '>=', from_date), # XXX correct for virtual?
            ('date', '<=', to_date),
            
            # TODO state filter
            ])
        debug_file.write('\n\nload picking:\n') # XXX DEBUG       
        for pick in pick_pool.browse(self.cr, self.uid, pick_ids):
            for line in pick.move_lines:
                if line.product_id.id in product_ids: # only supplier prod.
                    # TODO check state of line??                    
                    default_code = line.product_id.default_code
                    if line.state == 'assigned': # virtual
                        _logger.info('\nOF virtual: %s - %s [%s]\n' % (
                            line.picking_id.name,
                            default_code,
                            line.product_uom_qty,
                            ))
                        if default_code not in loads:
                            virtual_loads[default_code] = line.product_uom_qty
                        else:    
                            virtual_loads[default_code] += line.product_uom_qty
                        debug_file.write('Virtual: %s [%s]\n' % (
                            default_code, line.product_uom_qty)) # XXX DEBUG
                    elif line.state == 'done':
                        _logger.info('OF load: %s - %s [%s]\n' % (
                            line.picking_id.name,
                            default_code,
                            line.product_uom_qty,
                            ))
                        if default_code not in loads:
                            loads[default_code] = line.product_uom_qty
                        else:    
                            loads[default_code] += line.product_uom_qty
                        debug_file.write('Load: %s [%s]\n' % (
                            default_code, line.product_uom_qty)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Get order to delivery
        # ---------------------------------------------------------------------
        orders = {}
        sol_ids = sol_pool.search(self.cr, self.uid, [
            ('product_id', 'in', product_ids)])
            
        debug_file.write('\n\nOrder remain:\n') # XXX DEBUG
        for line in sol_pool.browse(self.cr, self.uid, sol_ids):
            # -------
            # Header:
            # -------            
            # check state:
            if line.order_id.state in ('cancel', 'draft', 'sent'): #done?
                continue
            
            # ------
            # Lines:
            # ------            
            # Check delivered:
            remain = line.product_uom_qty - line.delivered_qty
            if remain <= 0.0:
                continue
            
            default_code = line.product_id.default_code
            if default_code in orders:
                orders[default_code] += remain
            else:
                orders[default_code] = remain
            _logger.info('Order considered: %s - %s [%s]\n' % (
                line.order_id.name,
                default_code,
                remain,
                )) # XXX DEBUG
            debug_file.write('Product : %s [%s]\n' % (
                default_code, remain)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Transform in iteritems for report:
        # ---------------------------------------------------------------------
        res = []
        for key in sorted(products):
            default_code = products[key].default_code
            inventory = products[key].inventory_start or 0.0
            load = loads.get(default_code, 0.0)
            unload = unloads.get(default_code, 0.0)
            order = orders.get(default_code, 0.0)
            procurement = virtual_loads.get(default_code, 0.0)
            dispo = inventory + load - unload
            virtual = dispo + procurement - order
            res.append(
                (products[key],
                int(inventory),
                int(load), 
                int(unload), 
                int(order), 
                int(procurement), 
                int(dispo), 
                int(virtual),
                ))
        return res        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
