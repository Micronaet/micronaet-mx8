# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class AccountInvoice(orm.Model):
    ''' Model name: Invoice
    '''    
    _inherit = 'account.invoice'

    # BUtton event:    
    def update_parcels_event(self, cr, uid, ids, context=None):
        ''' Get total of parcels
        '''
        assert len(ids) == 1, 'Only one element a time'
        
        parcels = 0
        parcels_note = ''
        for line in self.browse(cr, uid, ids, context=context)[0].invoice_line:
            if line.product_id.exclude_parcels:
                continue # jump no parcels element
            qty = line.quantity
            q_x_pack = line.product_id.q_x_pack
            if q_x_pack > 0:
                if qty % q_x_pack > 0:
                    parcels_note += _('%s not correct q x pack\n') % (
                        line.product_id.default_code)
                else:
                    parcel = int(qty / q_x_pack)
                    parcels += parcel 
                    parcels_note += _('%s: parcels [%s x] %s \n') % (
                        line.product_id.default_code, q_x_pack, parcel)
            else:
                parcels_note += _(
                    '%s no q x pack\n') % line.product_id.default_code    

        self.write(cr, uid, ids, {
            'parcels': parcels,
            'parcels_note': parcels_note,
            }, context=context)            
                
    def update_parcels_volume_event(self, cr, uid, ids, context=None):
        ''' Calculate volume box and extract Excel calc file used:
        '''
        assert len(ids) == 1, 'Use only for a single id at a time.'
        
        # ---------------------------------------------------------------------
        # Excel file to evaluate volume data calc:
        # ---------------------------------------------------------------------
        excel_pool = self.pool.get('excel.writer')
        ws_name = 'Controllo volumi'
        excel_pool.create_worksheet(ws_name)

        # Load formats:
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        
        f_text = excel_pool.get_format('text')
        f_text_red = excel_pool.get_format('bg_red')

        f_number = excel_pool.get_format('number')
        f_number_red = excel_pool.get_format('bg_red_number')
        
        # Setup columns width:
        width = [
            15, 35,
            8, 8, 8, 8,
            10, 10, 10, 10, 10, 
            ]
        excel_pool.column_width(ws_name, width)
        
        invoice = self.browse(cr, uid, ids, context=context)[0]
        # ---------------------------------------------------------------------
        # Title
        # ---------------------------------------------------------------------
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, ['Fattura: %s del %s [Cliente: %s]' % (
                invoice.number or '???',
                invoice.date_invoice,
                invoice.partner_id.name,
                )], default_format=f_title)
        row += 2

        # ---------------------------------------------------------------------
        # Print header
        # ---------------------------------------------------------------------
        header = [
            'Codice', 'Descrizione', 

            # Unit:
            'Q x pack', 'Colli', 'Volume', 'm/l',
            
            # Total:
            'Q.', 'Colli', 'Pallet', 'Tot. volume', 'Tot. m/l',
            ]
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=f_header)
        
        # ---------------------------------------------------------------------
        # Print header
        # ---------------------------------------------------------------------
        # Init setup:
        total_volume = 0.0
        total_ml = 0.0
        total_colls = 0.0
        total_pallet = 0.0

        row_start = row + 1
        for line in invoice.invoice_line:
            row += 1

            product = line.product_id
            qty = line.quantity

            # Unit:
            q_x_pack = product.q_x_pack
            volume_1 = product.volume
            colls_1 = product.colls
            ml_1 = product.linear_length
            
            # Total:
            volume = qty * volume_1
            ml = qty * ml_1
            colls = qty // (q_x_pack or 1.0) + (
                1.0 if qty % (q_x_pack or 1.0) else 0.0)
            
            pallet = 0.0 # TODO     
                            
            total_volume += volume
            total_ml += ml
            total_colls += colls
            total_pallet += pallet
            
            if volume and ml:
                f_text_color = f_text
                f_number_color = f_number
            else:
                f_text_color = f_text_red
                f_number_color = f_number_red

            data = [
                (product.default_code or '/', f_text_color),
                (product.name or '/', f_text_color),
                
                int(q_x_pack),
                colls_1,
                volume_1,
                ml_1,
                
                qty, 
                colls,
                pallet,
                volume,
                ml,
                ]

            excel_pool.write_xls_line(
                ws_name, row, data,
                default_format=f_number_color
                )
        row_end = row

        # ---------------------------------------------------------------------
        # Total line:
        # ---------------------------------------------------------------------
        row += 1

        # Pallet:
        for col, total in (
                (7, total_colls), 
                (8, total_pallet), 
                (9, total_volume),
                (10, total_ml),
                ):
            formula = '=SUM(%s:%s)' % (
                excel_pool.rowcol_to_cell(row_start, col),
                excel_pool.rowcol_to_cell(row_end, col),
                )
            excel_pool.write_formula(
                ws_name, row, col, formula, f_number, total)
        
        
        self.write(cr, uid, ids, {
            'volume_note': _(u'[Volume: %s m³]  [Lung.: %s m/l]') % (
                #, Colli: %s, Pallet: %s') % (
                total_volume,
                total_ml,
                #total_colls,
                #total_pallet,
                )}, context=context)        
        return excel_pool.return_attachment(cr, uid, 'Volume')
    
    _columns = {
        'parcels_note': fields.text(
            'Parcel note', help='Calculation procedure note') ,
        'volume_note': fields.text('Volume'),
        }            

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
