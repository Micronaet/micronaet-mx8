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

    # -------------------------------------------------------------------------
    #                             Wizard button event
    # -------------------------------------------------------------------------
    def print_report(self, cr, uid, ids, context=None):
        ''' Print report product
        '''
        if context is None: 
            context = {}

        wiz_proxy = self.browse(cr, uid, ids)[0]
            
        datas = {}
        datas['wizard'] = True # started from wizard
        datas['partner_id'] = wiz_proxy.partner_id.id
        datas['partner_name'] = wiz_proxy.partner_id.name
        datas['default_code'] = wiz_proxy.default_code or False
        datas['categ_ids'] = [item.id for item in wiz_proxy.categ_ids]
        datas['categ_name'] = [item.name for item in wiz_proxy.categ_ids]
        datas['catalog_ids'] = [item.id for item in wiz_proxy.catalog_ids]
        datas['catalog_name'] = [item.name for item in wiz_proxy.catalog_ids]
        datas['status'] = wiz_proxy.status or False
        datas['sortable'] = wiz_proxy.sortable or False
        datas['with_photo'] = wiz_proxy.with_photo
        datas['statistic_category'] = [
            item.strip() for item in (
                wiz_proxy.statistic_category or '').split('|')]
                       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock_status_report',
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
        }
        
    _defaults = {
        'with_photo': lambda *x: True,
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


