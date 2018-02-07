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


class StockMoveExtractXlsWizard(orm.TransientModel):
    ''' Wizard for extract stock move in XLSX
    '''
    _name = 'stock.move.extract.xls.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_done(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        # Pool used
        move_pool = self.pool.get('stock.move')
        xls_pool = self.pool.get('excel.writer')

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        total_code = wiz_browse.total_code

        # ---------------------------------------------------------------------        
        # Create domain depend on parameter passed:
        # ---------------------------------------------------------------------        
        domain = []     
        # Date:        
        if wiz_browse.from_date:
            domain.append(
                ('picking_id.min_date', '>=',
                    '%s 00:00:00' % wiz_browse.from_date),
                )
        if wiz_browse.to_date:
            domain.append(
                ('picking_id.min_date', '<=',
                    '%s 23:59:59' % wiz_browse.to_date),
                )
        
        if wiz_browse.partner_id:
            domain.append(
                ('picking_id.partner_id', '=', wiz_browse.partner_id.id),
                )
        if wiz_browse.product_id:
            domain.append(
                ('product_id', '=', wiz_browse.product_id.id),
                )
        if wiz_browse.origin:
            domain.append(
                ('picking_id.origin', 'ilike', origin),
                )
        if wiz_browse.picking_type_id:
            domain.append(
                ('picking_id.picking_type_id', '=',
                    wiz_browse.picking_type_id.id),
                )

        # Last filter:
        domain.extend([
            ('state', '=', 'done'),
            ])
            
        # Create Excel WB
        ws_product = _('Movimenti magazino')
        xls_pool.create_worksheet(ws_product)
        xls_pool.write_xls_line(ws_product, 0, [
            'Partner', 'Orgine', 'Prelievo', 'Data pianificata', 'Tipo', 
            'Codice', 'Nome', 'Descrizione', 'Q.', 'UM'])
        xls_pool.column_width(ws_product, [55, 20, 20, 30, 20, 25, 40, 20, 10])
        
        # Total
        total_db = {}
        move_ids = move_pool.search(cr, uid, domain, context=context)        
        row = 0
        _logger.warning('Total move selected: %s' % len(move_ids))        
        for move in sorted(move_pool.browse(
                cr, uid, move_ids, context=context),
                key=lambda x: x.picking_id.min_date):
            row += 1               
            product = move.product_id
            qty = move.product_uom_qty
            xls_pool.write_xls_line(
                ws_product, row, [
                    move.picking_id.partner_id.name,
                    move.picking_id.origin,
                    move.picking_id.name,
                    move.picking_id.min_date,
                    move.picking_id.picking_type_id.name,
                    product.default_code,
                    product.name,
                    move.name, # Use move description
                    qty, 
                    move.product_uom.name,
                    ])
            # Total block:
            if total_code:
                if product not in total_db:
                    total_db[product] = 0.0
                total_db[product] += qty

            if not(row % 100):
                _logger.info('... Exporting: %s' % row)
        
        # ---------------------------------------------------------------------
        # Total code page:        
        # ---------------------------------------------------------------------
        if total_code:
            row = 0
            ws_total = _('Totali per codice')
            xls_pool.create_worksheet(ws_total)
            xls_pool.write_xls_line(ws_total, row, [
                'Codice', 'Descrizione', 'Totale'])
            xls_pool.column_width(ws_total, [20, 45, 10])
            for product in sorted(total_db, key=lambda x: x.default_code):                
                row += 1
                qty = total_db[product]
                xls_pool.write_xls_line(
                    ws_total, row, [
                        product.default_code,
                        product.name,
                        qty,
                        ])
            
        return xls_pool.return_attachment(
            cr, uid,
            'Movimenti di magazzino', 'movimenti_di_magazzino.xlsx', 
            context=context)

    _columns = {
        'total_code': fields.boolean('Totalizzatore', 
            help='Aggiunte pagina con totale per codice'),
        'from_date': fields.date('From date'),
        'to_date': fields.date('To date'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'product_id': fields.many2one('product.product', 'Product'),
        'origin': fields.char('Origin', size=20),
        'picking_type_id': fields.many2one(
            'stock.picking.type', 'Picking type', required=False),
        # TODO state?
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
