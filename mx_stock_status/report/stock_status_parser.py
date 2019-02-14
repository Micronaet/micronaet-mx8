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
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)

class ProductProdcut(orm.Model):
    """ Model name: ProductProdcut
    """
    
    _inherit = 'product.product'
    
    # -------------------------------------------------------------------------
    #                         UTILITY USED IN PARSER:
    # -------------------------------------------------------------------------
    def mx_stock_status_get_filter(self, data):
        ''' Get filter function used in parser
        '''
        if data is None:
            data = {}
        res = ''
        
        partner_name = data.get('partner_name', False)        
        default_code = data.get('default_code', False)        
        statistic_category = data.get('statistic_category', False)        
        categ_name = data.get('categ_id', False)
        catalog_name = data.get('catalog_id', False)
        status = data.get('status', False)
        sortable = data.get('sortable', False)
        with_photo = data.get('with_photo', False)
        with_stock = data.get('with_stock', False)
        mode = data.get('mode', False)
        
        # Mode: 
        res += _('Modo: %s; ') % mode
        
        # Partner:
        if partner_name:
            res += _('Fornitore: %s; ') % partner_name
        
        # Product:    
        if default_code:
            res += _('Codice: %s; ') % default_code
        if statistic_category:
            res += _('Categoria statistica: %s; ') % statistic_category
        if categ_name:
            res += _('Categoria: %s; ') % categ_name
        if catalog_name:
            res += _('Catalogo: %s; ') % catalog_name
        if status:
            res += _('Stato: %s; ') % status
        if sortable:
            res += _('Prodotti ordinabili; ')
            
        if mode == 'status':            
            # Photo:            
            if with_photo:
                res += _('Con foto; ')
            else:    
                res += _('Senza foto; ')
        else: # simple
            # Stock:            
            if with_stock:
                res += _('Solo esistenti; ')
            else:    
                res += _('Tutti; ')            
        return res

    def get_picking_last_date(self, cr, uid, code=False, load_all=False, 
            context=None):
        ''' Function used in parser for last picking date
        '''
        if context is None:
            context = {}

        detailed = context.get('detailed', False)
 
        if load_all: # no code = load data
            self._picking_date = {}
            self._picking_detailed = {}
            line_pool = self.pool.get('stock.move')

            line_ids = line_pool.search(cr, uid, [
                ('state', '=', 'done'),
                ('picking_id.picking_type_id.code', '=', 'incoming'),
                ], order='date desc', context=context)
            
            for line in line_pool.browse(
                    cr, uid, line_ids, context=context):
                code = line.product_id.default_code or False
                date = line.date or line.create_date
            
                if not code:
                    continue
                    
                if code not in self._picking_date or \
                        date > self._picking_date[code]:
                    # Update:
                    picking = line.picking_id
                    self._picking_date[code] = date                        
                    self._picking_detailed[code] = '%s del %s (%s >> %s)' % (
                        picking.name or '',                        
                        picking.bf_number or '',
                        (date or '')[:10],
                        picking.origin,
                        )
            return '' # First load

        if detailed:    
            return (
                self._picking_date.get(code, '/'),
                self._picking_detailed.get(code, '/'),
                )
                
        else:
            return self._picking_date.get(code, '/')    
        
    def get_purchase_last_date(self, cr, uid, code=False, load_all=False, 
            context=None):
        ''' Function used in parser for last purchase date
        '''       
        if context is None:
            context = {}
        detailed = context.get('detailed', False)
 
        if load_all: # no code = load data
            self._purchase_date = {}
            self._purchase_detailed = {}
            line_pool = self.pool.get('purchase.order.line')
            line_ids = line_pool.search(cr, uid, [
                ('order_id.state', 'not in', ('draft', 'cancel', 'sent')),
                ], order='date_planned desc', context=context)
            
            for line in line_pool.browse(
                    cr, uid, line_ids, context=context):
                code = line.product_id.default_code or False
                date = line.date_planned or \
                    line.order_id.minimum_date_planned or \
                    line.order_id.date_order
            
                if not code:
                    continue
                    
                if code not in self._purchase_date or \
                        date > self._purchase_date[code]:
                    # Update:
                    order = line.order_id
                    self._purchase_date[code] = date                        
                    self._purchase_detailed[code] = '%s del %s' % (
                        order.name or '',
                        date,
                        #picking.bf_number or '',
                        )
            return ''

        if detailed:    
            return self._purchase_detailed.get(code, '/')    
        else:
            return self._purchase_date.get(code, '/')    
            
    def stock_status_report_get_object(self, cr, uid, data=None, context=None):
        ''' Keep function here for call extra parser
        '''
        if data is None:
            data = {}
            
        # Pool used:
        partner_pool = self.pool.get('res.partner')
        product_pool = self.pool.get('product.product')
        supplier_pool = self.pool.get('product.supplierinfo')

        # =====================================================================
        #                            GENERATE FILTER:
        # =====================================================================
        product_ids = []

        # ---------------------------------------------------------------------
        # SUPPLIER FILTER:
        # ---------------------------------------------------------------------
        partner_id = data.get('partner_id', False)        
        default_code = data.get('default_code', False)        
        statistic_category = data.get('statistic_category', False)        
        categ_ids = data.get('categ_ids', False)
        catalog_ids = data.get('catalog_ids', False)
        status = data.get('status', False)
        sortable = data.get('sortable', False)
        inventory_category_id = data.get('inventory_category_id', False)
        #mode = data.get('mode', False)
        #with_stock = data.get('with_stock', False)
                
        if partner_id:
            # -----------------------------------------------------------------
            # A. Get template product supplier by partner (supplier in product)
            # -----------------------------------------------------------------
            supplierinfo_ids = supplier_pool.search(cr, uid, [
                ('name', '=', partner_id)], context=context)
            product_tmpl_ids = []
            for supplier in supplier_pool.browse(
                    cr, uid, supplierinfo_ids, context=context):
                product_tmpl_ids.append(supplier.product_tmpl_id.id) 
            # Get product form template:
            tmpl_product_ids = product_pool.search(cr, uid, [
                ('product_tmpl_id', 'in', product_tmpl_ids)], context=context)
            product_ids.extend(tmpl_product_ids)

            # -----------------------------------------------------------------
            # B. Get product supplier by partner (field: first_supplier_id
            # -----------------------------------------------------------------
            first_supplier_product_ids = product_pool.search(
                cr, uid, [
                    ('first_supplier_id', '=', partner_id)], context=context)
            product_ids.extend(first_supplier_product_ids)

        # ---------------------------------------------------------------------
        # PRODUCT FILTER:
        # ---------------------------------------------------------------------
        domain = []
        if product_ids: # filtered for partner
            domain.append(('id', 'in', product_ids))

        if default_code: 
            domain.append(('default_code', 'ilike', default_code))

        if statistic_category:            
            domain.append(('statistic_category', 'in', statistic_category))

        if categ_ids:
            domain.append(('categ_id', 'in', categ_ids))

        if catalog_ids: # TODO test
            domain.append(('catalog_ids', 'in', catalog_ids))

        if status:
            domain.append(('status', '=', status))

        if sortable:
            domain.append(('sortable', '=', True))
            
        if inventory_category_id:
            domain.append(
                ('inventory_category_id', '=', inventory_category_id))
                
        # TODO ADD other (and filter)
        
        #if mode == 'simple' and with_stock: 
        #    domain.append(('mx_net_qty', '>', 0))

        product_ids = product_pool.search(cr, uid, domain, context=context)
        products = product_pool.browse(cr, uid, product_ids, context=context)
        return products

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_object': self.get_object,
            'get_date': self.get_date,
            'get_filter': self.get_filter,
            'get_purchase_last_date': self.get_purchase_last_date,
            'get_duty_for_product': self.get_duty_for_product,
            'clean_gamma': self.clean_gamma,
        })

    def clean_gamma(self, gamma):
        ''' Clean some gamma terms
        '''
        if gamma == 'Fuori catalogo':
            return 'OUT'
        elif gamma == 'Catalogo':
            return 'Cat.'
        else:
            return gamma
            
    def get_duty_for_product(self, product):
        ''' Get duty info for product (proxy)
        '''
        product_pool = self.pool.get('product.product')
        return product_pool.get_duty_this_product_rate(product)
        
    def get_purchase_last_date(self, code=False, load_all=False):
        ''' Get filter selected
        '''
        cr = self.cr
        uid = self.uid
        context = {}
        return self.pool.get('product.product').get_purchase_last_date(
            cr, uid, code=False, load_all=False, context=context)

    def get_date(self, ):
        ''' Get filter selected
        '''
        return datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

    def get_filter(self, data):        
        ''' Get filter selected
        '''
        return self.pool.get('product.product').mx_stock_status_get_filter(
            data)
    
    def get_object(self, data):
        ''' Search all product elements
        '''
        return self.pool.get('product.product').stock_status_report_get_object(
            self.cr, self.uid, data=data)#, context=context)
      
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
