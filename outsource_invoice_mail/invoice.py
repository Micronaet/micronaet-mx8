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
    """ Model name: AccountInvoice
    """    
    _inherit = 'account.invoice'

    # -------------------------------------------------------------------------
    # Store function:
    # -------------------------------------------------------------------------
    def send_mail_invoice_marketed_product(self, cr, uid, days=2, 
            context=None):
        ''' Send mail with line with marketed product for last X days
        '''    
        _logger.info('Launch marketed product invoiced, days: %s' % days)
        
        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        WS_name = _('Fatture commercializzati')        
        excel_pool.create_worksheet(WS_name)
        
        # ---------------------------------------------------------------------
        # Format used:
        # ---------------------------------------------------------------------
        title_text = excel_pool.get_format('title')
        header_text = excel_pool.get_format('header')
        
        row_text_white = excel_pool.get_format('text')
        row_number_white = excel_pool.get_format('number')

        row_text_red = excel_pool.get_format('text_red')
        row_number_red = excel_pool.get_format('number_red')
        
        # ---------------------------------------------------------------------
        # Title:
        # ---------------------------------------------------------------------
        title = 'Prodotti fatturati commercializzati: [Data: %s]' % (
            datetime.now(),
            )

        row = 0
        excel_pool.write_xls_line(
            WS_name, row, [title, ], default_format=title_text)
        
        # ---------------------------------------------------------------------
        # Header:
        # ---------------------------------------------------------------------
        row += 2
        excel_pool.write_xls_line(
            WS_name, row, [
                # Header:
                'Numero',
                'Cliente',
                'Data',
                
                # Detail:
                'Codice',
                'Descrizione',
                'Q.',
                'Prezzo',
                'Sconti',
                'Subtotale',
                ], default_format=header_text)

        excel_pool.column_width(WS_name, [
            # Header:
            15, 40, 10,
            
            # Detail:
            10, 40, 10, 10, 10, 10,         
            ])

        # ---------------------------------------------------------------------
        # Detail:
        # ---------------------------------------------------------------------        
        now = datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT)
        from_date = (datetime.now() - timedelta(days=days)).strftime(
            DEFAULT_SERVER_DATE_FORMAT)
        line_pool = self.pool.get('account.invoice.line')        
        line_ids = line_pool.search(cr, uid, [
            ('product_id.marketed', '=', True),
            ('invoice_id.date_invoice', '>=', from_date),
            ], context=context)
        if not line_ids:
            _logger.warning('No invoice line with marketed product!')            
            excel_pool.close_workbook() # remove file
            return True
            
        for line in sorted(
                line_pool.browse(cr, uid, line_ids, context=context),
                key=lambda x: (
                    x.invoice_id.date_invoice, 
                    x.invoice_id.partner_id.name,
                    x.invoice_id.number,
                    ),
                reverse=True,
                ):
            row += 1
            if line.invoice_id.date_invoice == now:
                row_text = row_text_red                
                row_number = row_number_red
            else:
                row_text = row_text_white            
                row_number = row_number_white
                
            excel_pool.write_xls_line(
                WS_name, row, [
                    # Header:
                    line.invoice_id.number,
                    line.invoice_id.partner_id.name,
                    line.invoice_id.date_invoice,
                    
                    # Detail:
                    line.product_id.default_code,
                    line.name,
                    (line.quantity, row_number),
                    (line.price_unit, row_number),
                    (line.multi_discount_rates, row_number),
                    (line.price_subtotal, row_number),
                    ], default_format=row_text)
        
        excel_pool.send_mail_to_group(cr, uid, 
            'outsource_invoice_mail.'
            'group_report_mail_marketed_product_manager',
            'Righe fattura con prodotti commercializzati', 
            'Elenco righe fatture con prodotti commercializzati.', 
            'commercializzati.xlsx', # Mail data
            context=None)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
