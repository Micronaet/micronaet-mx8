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
    def send_mail_invoice_marketed_product(
            self, cr, uid, days=2, context=None):
        """ Send mail with line with marketed product for last X days
        """
        _logger.info('Launch marketed product invoiced, days: %s' % days)

        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        WS_name = _('Fatture commercializzati')
        excel_pool.create_worksheet(WS_name)

        # ---------------------------------------------------------------------
        # Format used:
        # ---------------------------------------------------------------------
        has_today = False # Not today event (for subject)
        title_text = excel_pool.get_format('title')
        header_text = excel_pool.get_format('header')

        row_text_white = excel_pool.get_format('text')
        row_number_white = excel_pool.get_format('number')

        row_text_red = excel_pool.get_format('text_red')
        row_number_red = excel_pool.get_format('number_red')

        now = datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT)
        from_date = (datetime.now() - timedelta(days=days)).strftime(
            DEFAULT_SERVER_DATE_FORMAT)

        row = 0 # Start line
        excel_pool.column_width(WS_name, [
            # Header:
            15, 40, 10,

            # Detail:
            10, 40, 10,
            # Invoice detail only
            10, 10, 10,
            ])

        # ---------------------------------------------------------------------
        #                                  DDT
        # ---------------------------------------------------------------------
        # Load data:
        move_pool = self.pool.get('stock.move')
        move_ids = move_pool.search(cr, uid, [
            # DDT confirmed not invoiced:
            # ('ddt_id.state', '=', 'confirmed'),
            ('picking_id.ddt_id.invoice_id', '=', False),

            ('product_id.marketed', '=', True),
            ], context=context)

        if move_ids:
            # Title:
            title = 'Prodotti commercializzati consegnati (DDT aperti)'
            excel_pool.write_xls_line(
                WS_name, row, [title, ], default_format=title_text)

            # Header:
            row += 2
            excel_pool.write_xls_line(
                WS_name, row, [
                    # Header:
                    'DDT Numero',
                    'Cliente',
                    'Data',

                    # Detail:
                    'Codice',
                    'Descrizione',
                    'Q.',
                    # 'Prezzo',
                    # 'Sconti',
                    # 'Subtotale',
                    ], default_format=header_text)

            # Detail:
            for move in sorted(
                    move_pool.browse(cr, uid, move_ids, context=context),
                    key=lambda x: (
                        x.ddt_id.date[:10],
                        x.ddt_id.partner_id.name,
                        x.ddt_id.name,
                        ),
                    reverse=True,
                    ):
                row += 1
                if move.ddt_id.date[:10] == now:
                    has_today = True
                    row_text = row_text_red
                    row_number = row_number_red
                else:
                    row_text = row_text_white
                    row_number = row_number_white

                excel_pool.write_xls_line(
                    WS_name, row, [
                        # Header:
                        move.ddt_id.name,
                        move.ddt_id.partner_id.name,
                        move.ddt_id.date[:10],

                        # Detail:
                        move.product_id.default_code,
                        move.name,
                        (move.product_uom_qty, row_number),
                        ], default_format=row_text)
        else:
            _logger.warning('DDT Table not writed')

        # ---------------------------------------------------------------------
        #                                  INVOICE
        # ---------------------------------------------------------------------
        # Load data:
        line_pool = self.pool.get('account.invoice.line')
        line_ids = line_pool.search(cr, uid, [
            ('product_id.marketed', '=', True),
            ('invoice_id.date_invoice', '>=', from_date),
            ], context=context)

        if line_ids: # no print table:
            # Title:
            title = 'Prodotti commercializzati fatturati: [Da: %s a: %s]' % (
                from_date, now)
            row += 2
            excel_pool.write_xls_line(
                WS_name, row, [title, ], default_format=title_text)

            # Header:
            row += 2
            excel_pool.write_xls_line(
                WS_name, row, [
                    # Header:
                    'Fattura Numero',
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

            # Detail:
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
                    has_today = True
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

        else:
            _logger.warning('Invoice Table not writed')

        # Send mail:
        if not line_ids and not move_ids:
            _logger.warning('No invoice line or DDT with marketed product!')
            excel_pool.close_workbook()  # remove file
            return True
        else:
            excel_pool.send_mail_to_group(
                cr, uid,
                'outsource_invoice_mail.'
                'group_report_mail_marketed_product_manager',
                'Righe fattura con prodotti commercializzati [%s]' % (
                    'PRESENTE OGGI' if has_today else 'NESSUNA NOVITA\'',
                    ),
                'Elenco righe fatture con prodotti commercializzati.',
                'commercializzati.xlsx',  # Mail data
                context=None)


class SaleOrder(orm.Model):
    """ Model name: Sale Order
    """
    _inherit = 'sale.order'

    # -------------------------------------------------------------------------
    # Store function:
    # -------------------------------------------------------------------------
    def send_mail_invoice_marketed_product_oc(
            self, cr, uid, days=2, context=None):
        """ Send mail with line with marketed product for last X days
        """
        _logger.info('Launch marketed product order, days: %s' % days)

        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        ws_name = _('Ordini commercializzati')
        excel_pool.create_worksheet(ws_name)

        # ---------------------------------------------------------------------
        # Format used:
        # ---------------------------------------------------------------------
        has_today = False  # Not today event (for subject)
        title_text = excel_pool.get_format('title')
        header_text = excel_pool.get_format('header')

        row_text_white = excel_pool.get_format('text')
        row_number_white = excel_pool.get_format('number')

        row_text_red = excel_pool.get_format('text_red')
        row_number_red = excel_pool.get_format('number_red')

        today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        from_date = (datetime.now() - timedelta(days=days)).strftime(
            DEFAULT_SERVER_DATE_FORMAT)

        row = 0  # Start line
        excel_pool.column_width(ws_name, [
            # Header:
            15, 40, 10,

            # Detail:
            10, 40, 10,
            # Invoice detail only
            10, 10, 10,
            ])

        # ---------------------------------------------------------------------
        #                                  DDT
        # ---------------------------------------------------------------------
        # Load data:
        line_pool = self.pool.get('sale.order.line')
        line_ids = line_pool.search(cr, uid, [
            ('order_id.state', 'not in', ('cancel', 'draft', 'sent')),
            ('order_id.date_order', '>=', from_date),
            ('product_id.marketed', '=', True),
            ], context=context)

        if line_ids:
            # Title:
            title = 'Prodotti commercializzati in OC'
            excel_pool.write_xls_line(
                ws_name, row, [title, ], default_format=title_text)

            # Header:
            row += 2
            excel_pool.write_xls_line(
                ws_name, row, [
                    # Header:
                    'Numero',
                    'Cliente',
                    'Data',

                    # Detail:
                    'Codice',
                    'Descrizione',
                    'Q.',
                    # 'Prezzo',
                    # 'Sconti',
                    # 'Subtotale',
                    ], default_format=header_text)

            # Detail:
            for line in sorted(
                    line_pool.browse(cr, uid, line_ids, context=context),
                    key=lambda x: (
                        x.order_id.date_order[:10],
                        x.order_id.partner_id.name,
                        x.order_id.name,
                        ),
                    reverse=True,
                    ):
                row += 1
                order = line.order_id
                date_order = order.date_order[:10]
                if date_order == today:
                    has_today = True
                    row_text = row_text_red
                    row_number = row_number_red
                else:
                    row_text = row_text_white
                    row_number = row_number_white

                excel_pool.write_xls_line(
                    ws_name, row, [
                        # Header:
                        order.name,
                        order.partner_id.name,
                        date_order,

                        # Detail:
                        line.product_id.default_code,
                        line.name,
                        (line.product_uom_qty, row_number),
                        ], default_format=row_text)
        else:
            _logger.warning('Sale order not written')

        # Send mail:
        if not line_ids:
            _logger.warning('No order line with marketed product!')
            excel_pool.close_workbook()  # remove file
            return True
        else:
            excel_pool.send_mail_to_group(
                cr, uid,
                'outsource_invoice_mail.'
                'group_report_mail_marketed_product_oc_manager',
                'Righe ordini con prodotti commercializzati [%s]' % (
                    'PRESENTE OGGI' if has_today else 'NESSUNA NOVITA\'',
                    ),
                'Elenco righe OC con prodotti commercializzati.',
                'commercializzati.xlsx',  # Mail data
                context=None)
