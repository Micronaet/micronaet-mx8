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
from openerp.osv import fields, osv, expression, orm

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
        company_pool = self.pool.get('res.company')
        partner_pool = self.pool.get('res.partner')
        product_pool = self.pool.get('product.product')
        supplier_pool = self.pool.get('product.supplierinfo')

        company_ids = company_pool.search(self.cr, self.uid, [])
        company_proxy = company_pool.browse(self.cr, self.uid, company_ids)[0]
        
        # ---------------------------------------------------------------------
        # Search partner in supplier info:
        # ---------------------------------------------------------------------
        partner_id = data.get('partner_id', False)        
        supplierinfo_ids = supplier_pool.search(self.cr, self.uid, [
            ('name', '=', partner_id)])           

        # ---------------------------------------------------------------------
        # A. Get template product supplier by partner (supplier under product)
        # ---------------------------------------------------------------------
        # XXX DEBUG:
        debug_f = '/home/administrator/photo/xls/status.txt'
        pickle_file = '/home/administrator/photo/dicts.pickle' # TODO
        debug_file = open(debug_f, 'w')

        product_tmpl_ids = []
        for supplier in supplier_pool.browse(
                self.cr, self.uid, supplierinfo_ids):
            product_tmpl_ids.append(supplier.product_tmpl_id.id) 
        
        debug_file.write('\nTemplate selected:\n%s\n' % (product_tmpl_ids)) # XXX DEBUG

        # ---------------------------------------------------------------------
        # B. Get product supplier by partner (field: first_supplier_id
        # ---------------------------------------------------------------------
        first_supplier_product_ids = product_pool.search(self.cr, self.uid, [
            ('first_supplier_id', '=', partner_id)])
            
        debug_file.write('\nFirst supplier product:\n%s\n' % (
            first_supplier_product_ids)) # XXX DEBUG

        # ---------------------------------------------------------------------
        # Get product form template:
        # ---------------------------------------------------------------------        
        product_ids = product_pool.search(self.cr, self.uid, [
            ('product_tmpl_id', 'in', product_tmpl_ids)])
        debug_file.write('\nProduct ID record (prod>suppl) %s' % (
            len(product_ids)))
            
        # Extend list:
        product_ids.extend(first_supplier_product_ids)
        debug_file.write('\nProduct ID record (suppl) %s' % (
            len(first_supplier_product_ids)))

        debug_file.write('\nProduct ID record totals %s' % (
            len(product_ids)))
        
        if not product_ids:
            raise osv.except_osv(
                _('Report error'),
                _('No data for this partner (no first suppl. or in product)',
                ))

        products = {}
        product_mask = company_proxy.product_mask or ''
        products_code = [] # For search in other database

        clean_product_ids = []
        for product in product_pool.browse(self.cr, self.uid, product_ids):                
            default_code = product.default_code
            products_code.append(product_mask % default_code)
            if default_code in products:
                # Jump bouble (TODO use sets not list!!!)
                continue
            products[default_code] = product
            clean_product_ids.append(product.id)
            
        product_ids = clean_product_ids # TODO not so clean ... use sets!!!
        debug_file.write('\nProduct ID record cleaned %s\n' % (
            len(product_ids)))

        debug_file.write('\n\nProduct code searched in other DB\n%s' % (
            products_code, )) # XXX DEBUG
        debug_file.write('\n\nProduct selected:\n%s' % (
            product_ids,)) # XXX DEBUG
        
        # ----------------------
        # Call master procedure:
        # ----------------------
        # MASTER:
        # products before
        unloads = {}
        loads = {}
        virtual_loads = {}
        orders = {}

        partner_pool.stock_movement_inventory_data(
            self.cr, self.uid, product_ids, False, debug_file,
            dicts=[
                loads, # load document
                unloads, # unload document
                orders, # order not delivered
                virtual_loads, # procurement not received
                ], 
            context=None)

        # =====================================================================
        # Call remote procedure:
        # =====================================================================
        # REMOTE:
        # products before
        remote_unloads = {}
        remote_loads = {}
        remote_virtual_loads = {}
        remote_orders = {}

        # TODO call XMLRPC procedure:
        # ERPPEEK CLIENT:

        erp = erppeek.Client(
            'http://%s:%s' % (
                company_proxy.remote_hostname, 
                company_proxy.remote_port),
            db=company_proxy.remote_name,
            user=company_proxy.remote_username,
            password=company_proxy.remote_password,
            )

        if not erp:
            raise osv.except_osv(
                _('XMLRPC error'),
                _('Cannot connect to second company',
                ))

        erp_partner_pool = erp.ResPartner
        
        # Pack dicts:
        dicts = (
            remote_loads, # load document
            remote_unloads, # unload document
            remote_orders, # order not delivered
            remote_virtual_loads, # procurement not received
            )
        
        # Pickle dump dict:    
        pickle_f = open(pickle_file, 'w')
        pickle.dump(dicts, pickle_f)
        pickle_f.close()
        
        # Close lof file:
        debug_file.close()
        
        both_products = erp_partner_pool.erpeek_stock_movement_inventory_data(
            products_code, debug_f)
            
        # Reopen for append:    
        debug_file = open(debug_f, 'a')    
        
        debug_file.write('\n\nCode in remote DB: %s\n\n' % (both_products, ))    
        # Pickle load dict:    
        pickle_f = open(pickle_file, 'r')
        dicts = pickle.load(pickle_f)
        pickle_f.close()
        
        # Unpack dict passed:
        (
            remote_loads, # TODO check if has records (maybe never!)
            remote_unloads, # TODO check if has records (maybe never!) 
            remote_orders, 
            remote_virtual_loads, # TODO check if has records (maybe never!)
            ) = dicts
        # =====================================================================
        
        # ---------------------------------------------------------------------
        # Transform in iteritems for report:
        # ---------------------------------------------------------------------
        res = []
        
        debug_file.write('\n\nInventory:\nCode;Q.\n')    
        for key in sorted(products):
            default_code = products[key].default_code
            remote_code = product_mask % default_code
            
            inventory = products[key].inventory_start or 0.0
            debug_file.write('%s;%s\n' % (
                default_code, inventory))
            # XXX NOTE remote not used!
            
            load = loads.get(default_code, 0.0) + \
                remote_loads.get(remote_code, 0.0) 
                
            unload = unloads.get(default_code, 0.0) + \
                remote_unloads.get(remote_code, 0.0)
                
            order = orders.get(default_code, 0.0) + \
                remote_orders.get(remote_code, 0.0)
                
            procurement = virtual_loads.get(default_code, 0.0) + \
                remote_virtual_loads.get(remote_code, 0.0)
                
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
