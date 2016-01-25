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
            
            # Utility:
            #'get_counter': self.get_counter,
            #'set_counter': self.set_counter,            
        })
    
    def get_object(self, data):
        ''' Search all product elements
        '''
        # pool used:
        product_pool = self.pool.get('product.product')
        supplier_pool = self.pool.get('product.supplierinfo')
        pick_pool = self.pool.get('stock.picking')
        sale_pool = self.pool.get('sale.order')
        # procurements?
        
        # ---------------------------------------------------------------------
        # Search partner in supplier info:
        # ---------------------------------------------------------------------
        partner_id = data.get('partner_id', False)        
        supplierinfo_ids = supplier_pool.search(self.cr, self.uid, [
            ('name', '=', partner_id)])           

        # ---------------------------------------------------------------------
        # Get template product suppleir by partner
        # ---------------------------------------------------------------------
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
                )
        # ---------------------------------------------------------------------
        # Get product form template:
        # ---------------------------------------------------------------------        
        product_ids = product_pool.search(self.cr, self.uid, [
            ('product_tmpl_id', 'in', product_tmpl_ids)])
        products = {}
        for product in product_pool.browse(self.cr, self.uid, product_ids):                
            default_code = product.default_code
            if default_code in products:
                _logger.error('More than one default_code %s' % default_code)                
            products[default_code] = product

        # ---------------------------------------------------------------------
        # Get unload picking
        # ---------------------------------------------------------------------
        unloads = {}
        out_picking_type_id = 3 # TODO
        pick_ids = pick_pool.search(self.cr, self.uid, [
            ('picking_type_id', '=', out_picking_type_id),
            # data filter
            # state filter
            ])
        for pick in pick_pool.browse(cr, uid, pick_ids):
            for line in pick.move_lines:
                # TODO check state of line??
                default_code = line.product_id.default_code
                if default_code not in unloads:
                    unloads[default_code] = line.product_uom_qty
                else:    
                    unloads[default_code] += line.product_uom_qty

        # ---------------------------------------------------------------------
        # Get unload picking
        # ---------------------------------------------------------------------
        loads = {}
        
        # ---------------------------------------------------------------------
        # Transform in iteritems for report:
        # ---------------------------------------------------------------------
        res = []
        for key in sorted(products):
            default_code = products[key].default_code
            inventory = products[key].inventory_start or 0.0
            load = loads.get(default_code, 0.0)
            unload = unloads.get(default_code, 0.0)
            order = 0.0
            procurement = 0.0
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
                )) # TODO
        return res        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
