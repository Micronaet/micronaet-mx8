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
import xlsxwriter # XLSX export
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

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'

    _columns = {
        'inventory_excluded': fields.boolean(
            'Escluso dal calcolo inventario',
            help='Viene conteggiato ma non valorizzato in inventario'),
    }

# ---------------------------------------------------------------------
# Utility:
# ---------------------------------------------------------------------
def write_header(current_WS, header, row=0, cell_format=False):
    """ Write header in first line:
    """
    col = 0
    for title in header:
        if cell_format:
            current_WS.write(row, col, title, cell_format)
        else:
            current_WS.write(row, col, title)
        col += 1
    return


class StockStatusPrintImageReportWizard(orm.TransientModel):
    """ Wizard for print stock status
    """
    _name = 'stock.status.print.image.report.wizard'

    def extract_xls_check_inventory_file(
            self, cr, uid, ids, data=None, context=None):
        """ Extract inventory as XLS extrenal files every category in different
            page
            TODO Correct and write better!!!
        """
        # ---------------------------------------------------------------------
        #                        XLS log export:
        # ---------------------------------------------------------------------
        filename = '/home/administrator/photo/output/post_inventory_table.xlsx'
        _logger.info('Extract: %s' % filename)
        WB = xlsxwriter.Workbook(filename)

        # ---------------------------------------------------------------------
        # Create work sheet:
        # ---------------------------------------------------------------------
        header = ['DB', 'CODICE', 'DESCRIZIONE', 'UM',
            'CAT. STAT.', 'CATEGORIA', 'FORNITORE', 'INV', 'INV. DELTA', 'MRP',
            'CATEGORIA INVENTARIO',
            'INVENTARIO 31/12', 'INVENTARIO 1/1', 'COSTO', 'MODIFICA',
            'DATA QUOTAZIONE',
            ]

        # Create element for empty category:
        WS = WB.add_worksheet('Controlli inventario')
        counter = 0
        write_header(WS, header)

        # ---------------------------------------------------------------------
        # Prepare price last buy check
        # ---------------------------------------------------------------------
        price_pool = self.pool.get('pricelist.partnerinfo')
        price_ids = price_pool.search(cr, uid, [],
            order='write_date DESC', context=context)

        price_db = {}
        for price in price_pool.browse(cr, uid, price_ids, context=context):
            product = price.product_id  # suppinfo_id.name
            # price.suppinfo_id.product_tmpl_id.id
            if product.id in price_db:
                continue
            price_db[product.id] = (
                price.price, price.write_date, price.date_quotation)

        # ---------------------------------------------------------------------
        # Prepare BOM check
        # ---------------------------------------------------------------------
        line_pool = self.pool.get('mrp.bom.line')
        line_ids = line_pool.search(cr, uid, [
            ('bom_id.bom_category', 'in', ('parent', 'dynamic', 'half')),
            ], context=context)

        in_bom_ids = [item.product_id.id for item in line_pool.browse(
            cr, uid, line_ids, context=context)]

        # TODO remove after print:
        with_parent_bom = False
        linked_bom = {}
        if with_parent_bom:
            linked_bom_ids = line_pool.search(cr, uid, [
                ('bom_id.bom_category', '=', 'parent'),
                ], context=context)
            for line in line_pool.browse(cr, uid, linked_bom_ids,
                    context=context):
                linked_bom[
                    line.product_id.id] = line.bom_id.product_id.default_code

        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        counter = 0
        for product in self.pool.get(
                'product.product').stock_status_report_get_object(
                    cr, uid, data=data, context=context):
            counter += 1

            price_item = price_db.get(product.id, ('', '', ''))

            # Write data in correct WS:
            WS.write(counter, 0, 'X' if product.id in in_bom_ids else '')  # A
            WS.write(counter, 1, product.default_code)  # B
            WS.write(counter, 2, product.name)  # C
            WS.write(counter, 3, product.uom_id.name or '')  # D
            WS.write(counter, 4, product.statistic_category or '')  # E
            WS.write(counter, 5, product.categ_id.name or '')  # F
            WS.write(
                counter, 6,
                product.seller_ids[0].name.name if product.seller_ids else (
                    product.first_supplier_id.name or ''))  # G
            WS.write(counter, 7, product.inventory_start or '')  # H
            WS.write(counter, 8, product.inventory_delta or '')  # I
            WS.write(counter, 9, product.mx_mrp_out or '')  # J
            WS.write(counter, 10, product.inventory_category_id.name)  # K
            WS.write(counter, 11, product.mx_history_net_qty or '')  # L
            WS.write(counter, 12, product.mx_start_qty or '')  # M
            WS.write(counter, 13, price_item[0])  # N
            WS.write(counter, 14, price_item[1])  # O
            WS.write(counter, 15, price_item[2])  # P
        return True

    def extract_stock_status_xls_inventory_file(
            self, cr, uid, ids, data=None, context=None):
        """ Extract inventory as XLS external files every category in different
            page
        """
        if context is None:
            context = {}

        product_pool = self.pool.get('product.product')

        # ---------------------------------------------------------------------
        #                        XLS log export:
        # ---------------------------------------------------------------------
        filename = '/tmp/inventory_status.xlsx'
        WB = xlsxwriter.Workbook(filename)
        WS = WB.add_worksheet(_('Inventario'))

        # ---------------------------------------------------------------------
        # Format:
        # ---------------------------------------------------------------------
        format_title = WB.add_format({
            'bold': True,
            'font_color': 'black',
            'font_name': 'Verdana',
            'font_size': 9,
            # 'align': 'center',
            # 'valign': 'vcenter',
            # 'bg_color': 'gray',
            # 'border': 1,
            # 'text_wrap': True,
            })
        format_header = WB.add_format({
            'bold': True,
            'font_color': 'black',
            'font_name': 'Verdana',
            'font_size': 9,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'gray',
            'border': 1,
            'text_wrap': True,
            })
        format_text = WB.add_format({
            'font_name': 'Courier 10 Pitch',
            'font_size': 8,
            # 'align': 'right',
            # 'bg_color': 'c1e7b3',
            'border': 1,
            # 'num_format': '0.00',
            })

        # ---------------------------------------------------------------------
        # Setup dimension:
        # ---------------------------------------------------------------------
        # Columns:
        WS.set_column('A:A', 15)
        WS.set_column('B:B', 40)
        WS.set_column('C:C', 5)
        WS.set_column('D:D', 8)
        WS.set_column('E:E', 10)

        WS.set_column('F:G', 15)

        WS.set_column('H:H', 35)

        WS.set_column('I:J', 16)
        WS.set_column('K:K', 4)
        WS.set_column('L:M', 16)
        WS.set_column('N:P', 8)
        WS.set_column('Q:Q', 5)
        WS.set_column('R:T', 8)

        # Rows:
        WS.set_row(3, 25)

        # ---------------------------------------------------------------------
        # Create work sheet:
        # ---------------------------------------------------------------------
        # Title:
        header = [
            'CODICE', 'DESCRIZIONE', 'UM', 'CAT. STAT.',
            'COLORE', 'GAMMA',
            'CATEGORIA', 'FORNITORE', 'RIF. FORNITORE', 'ULTIMO ACQ.', 'ATT.',
            'COSTO INV. SOLO ACQ.',
            'COSTO FOB FORN.', 'ESISTENZA', 'COSTO INV.', 'DAZI',
            'TRASPORTO', 'USD', 'COSTO EUR', 'DAZIO EUR', 'COSTO FIN. EUR',
            ]

        # Write 3 line of header:
        context['detailed'] = True  # Add extra information on last purchase
        write_header(
            WS, ['', 'RACCOLTA DATI PER INVENTARIO', ], 0, format_title)
        write_header(WS, [
            _('Filtro'),
            product_pool.mx_stock_status_get_filter(data),
            product_pool.get_picking_last_date(  # Load data for future call)
                cr, uid, code=False, load_all=True),
            ], 1, format_title)
        context['detailed'] = False  # Add extra information on last purchase
        context['full'] = True  # Add extra information on last purchase
        write_header(WS, header, 3, format_header)

        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        row = 3
        for o in product_pool.stock_status_report_get_object(
                    cr, uid, data=data, context=context):
            row += 1
            year = str(datetime.now().year)

            # Calculate:
            duty = product_pool.get_duty_this_product_rate(o)  # L
            cost_fob = o.standard_price  # I
            usd = o.inventory_cost_exchange  # N
            transport = o.inventory_cost_transport  # M

            if o.seller_ids:
                supplier = \
                    o.first_supplier_id.name or o.seller_ids[0].name.name  # F
                supplier_ref = '%s %s' % (
                    o.seller_ids[0].product_code or '',
                    o.seller_ids[0].product_name or '',
                    )  # G
            else:
                supplier = o.first_supplier_id.name or '?'  # F
                supplier_ref = '?'

            purchase_date, purchase_reference, purchase_price = \
                product_pool.get_picking_last_date(
                    cr, uid, o.default_code, context=context)

            if usd:
                cost_eur = purchase_price / usd  # O  (ex. costo_fob)
                cost_duty_eur = purchase_price * duty / 100.0 / usd  # P
                cost_end_eur = cost_eur + cost_duty_eur + transport  # Q
            else:
                cost_eur = 'ERR'  # O
                cost_duty_eur = 'ERR'  # P
                cost_end_eur = 'ERR'  # Q

            # Check if is this year:
            this_year = purchase_date[:4] == '2023'  # year

            # Write data in correct WS:
            WS.write(row, 0, o.default_code or '????', format_text)  # A
            WS.write(row, 1, o.name or '', format_text)  # B
            WS.write(row, 2, o.uom_id.name or '', format_text)  # C
            WS.write(row, 3, o.statistic_category or '', format_text)  # D

            WS.write(row, 4, o.colour or '', format_text)  # E
            WS.write(row, 5, o.status or '', format_text)  # F

            WS.write(row, 6, o.categ_id.name or '', format_text)  # G
            WS.write(row, 7, supplier, format_text)  # H
            WS.write(row, 8, supplier_ref, format_text)  # I
            WS.write(row, 9, purchase_reference, format_text)  # J

            # todo CAMBIARE:
            WS.write(row, 10, 'X' if this_year else '', format_text)  # K
            WS.write(
                row, 11, o.inventory_cost_only_buy or '', format_text)  # L
            WS.write(
                row, 12, purchase_price, format_text)  # M (da pick-OF-prezzo)
            WS.write(
                row, 13,
                o.mx_net_qty if data.get('with_stock', False) else '/',
                format_text)  # N
            WS.write(row, 14, o.inventory_cost_no_move, format_text)  # O

            # Only if bought in this year:
            WS.write(row, 15, duty if this_year else 0.0, format_text)  # P
            WS.write(
                row, 16, transport if this_year else 0.0, format_text)  # Q
            WS.write(row, 17, usd if this_year else 0.0, format_text)  # R
            WS.write(row, 18, cost_eur if this_year else 0.0, format_text)  # S
            WS.write(
                row, 19, cost_duty_eur if this_year else 0.0, format_text)  # T
            WS.write(
                row, 20, cost_end_eur if this_year else 0.0, format_text)  # U
        WB.close()

        # ---------------------------------------------------------------------
        # Generate attachment for return file:
        # ---------------------------------------------------------------------
        attachment_pool = self.pool.get('ir.attachment')
        b64 = open(filename, 'rb').read().encode('base64')
        attachment_id = attachment_pool.create(cr, uid, {
            'name': 'Temp report',
            'datas_fname': 'stato_inventario.xlsx',
            'type': 'binary',
            'datas': b64,
            'partner_id': 1,
            'res_model': 'res.partner',
            'res_id': 1,
            }, context=context)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/saveas?model=ir.attachment&field=datas&'
                   'filename_field=datas_fname&id=%s' % attachment_id,
            'target': 'self',
            }

    def extract_old_xls_inventory_file(
            self, cr, uid, ids, data=None, context=None):
        """ Extract inventory as XLS external files every category in different
            page old version (from anagraphic)
        """
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        def write_header(current_WS, header):
            """ Write header in first line:
            """
            col = 0
            for title in header:
                current_WS.write(0, col, title)
                col += 1
            return

        def get_last_cost(product):
            """ Get last (supplier, cost)
            """
            res = [
                False,  # 0. Date
                '',  # 1. Supplier
                0.0,  # 2. Price
                0,  # 3. Number of price found
                '',  # 4. Note
                product.standard_price,  # 5. Manual cost
                product.weight,  # 6. weight (for pipes)
                ]  # Date, supplier, price, #

            default_code = product.default_code or ''
            if default_code.startswith('MT'):
                parent_code = default_code[:7]
            else:
                parent_code = default_code[:6]

            if product.relative_type == 'half':  # Product is HW
                no_price = False
                for line in product.half_bom_ids:
                    cost = get_last_cost(line.product_id)[2]
                    price = line.product_qty * cost
                    if not price:
                        no_price = True
                    res[2] += price
                    res[4] += '[%s >> q. %s x %s = %s]' % (
                        line.product_id.default_code or '',
                        line.product_qty,
                        cost,
                        price,
                        )
                if no_price:
                    res[2] = 0.0
                    res[4] = 'UN PREZZO A ZERO!: %s' % res[4]

            elif parent_code in self.parent_bom_cost:
                res[2] = self.parent_bom_cost[parent_code]
                res[1] = _('Preso da DB: %s') % parent_code
            elif product.is_pipe:
                try:
                    price = product.pipe_material_id.last_price
                except:
                    price = 0.0
                res[2] = product.weight * price
                res[4] += '[Kg. %s x %s = %s]' % (
                    weight,
                    price,
                    res[2],
                    )
            else:  # Product is normal product
                i = 0
                for supplier in product.seller_ids:
                    for price in supplier.pricelist_ids:
                        i += 1
                        # TODO check is_active?!?!?
                        if not res[0] or price.date_quotation > res[0]:
                            res[0] = price.date_quotation
                            res[1] = supplier.name.name
                            res[2] = price.price
                res[3] = i
            return res

        # ---------------------------------------------------------------------
        #                          START PROCEDURE:
        # ---------------------------------------------------------------------
        # todo keep in parameter!
        mode = 'current'  # 'start'
        _logger.warning('Stampa inventario valorizzato modo: %s' % mode)

        # Pool used:
        product_pool = self.pool.get('product.product')
        inv_pool = self.pool.get('product.product.inventory.category')
        excel_pool = self.pool.get('excel.writer')

        # ---------------------------------------------------------------------
        #                            Collect data:
        # ---------------------------------------------------------------------
        # Load parent bom if necessary:
        self.parent_bom_cost = {}  # reset value
        if 'bom_selection' in product_pool._columns:  # DB with BOM price mng.
            product_ids = product_pool.search(cr, uid, [
                ('bom_selection', '=', True),
                ], context=context)
            for p in product_pool.browse(
                    cr, uid, product_ids, context=context):
                default_code = p.default_code
                if not default_code:
                    continue
                if default_code.startswith('MT'):  # MT half worked
                    self.parent_bom_cost[default_code[:7]] = p.to_industrial
                else:  # Product
                    self.parent_bom_cost[default_code[:6]] = p.to_industrial

        # ---------------------------------------------------------------------
        # Search all inventory category:
        # ---------------------------------------------------------------------
        inv_ids = inv_pool.search(cr, uid, [], context=context)

        # ---------------------------------------------------------------------
        #                              EXCEL:
        # ---------------------------------------------------------------------
        if mode == 'current':
            inv_text = 'INV. ATT.'
        else:
            inv_text = 'INV. INIZ.'
        header = [
            'CODICE', 'DESCRIZIONE', 'UM',
            'FORNITORE', inv_text, 'DATA RIF.', '#', 'COSTO',
            'TOTALE', 'COSTO MANUALE', 'PESO',
            'NOTE',
            ]

        width = [
            15, 40, 3,
            25, 9, 9, 7, 8,
            10, 10, 10,
            70,
            ]

        ws_names = {  # Row position
            '': [1, 0.0, 0, ],  # Empty category (row, total, error):
            }
        ws_empty = 'Non assegnati'
        excel_pool.create_worksheet(ws_empty)

        # Load format:
        excel_pool.set_format(number_format='#,##0.####0')
        cell_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'text': excel_pool.get_format('text'),
            'number': excel_pool.get_format('number'),

            'bg': {
                'red': excel_pool.get_format('bg_red'),
                'green': excel_pool.get_format('bg_green'),
                },
            'bg_number': {
                'red': excel_pool.get_format('bg_red_number'),
                },
            }

        # Init setup:
        excel_pool.column_width(ws_empty, width)
        excel_pool.write_xls_line(ws_empty, 0, header, cell_format['header'])

        # Create all others category:
        for category in inv_pool.browse(cr, uid, inv_ids, context=context):
            category_name = category.name
            ws_names[category_name] = [1, 0.0, 0] # jump header
            excel_pool.create_worksheet(category_name)

            # Init setup remain pages:
            excel_pool.column_width(category_name, width)
            excel_pool.write_xls_line(
                category_name, 0, header, cell_format['header'])

        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        if mode == 'current':
            domain = [
                ('inventory_excluded', '=', False),  # Remove excluded element
                ]
        else:
            domain = [
                ('mx_start_qty', '>', 0.0),  # Only present start inventory
                ('inventory_excluded', '=', False),  # Remove excluded element
                ]

        product_ids = product_pool.search(cr, uid, domain, context=context)
        without_inventory = {}  # In current mode used for this page
        for product in sorted(
                product_pool.browse(cr, uid, product_ids, context=context),
                key=lambda x: (x.default_code, x.name)):
            category_name = product.inventory_category_id.name or ''

            (date, supplier, cost, number, note, standard_price,
                weight) = get_last_cost(product)

            if mode == 'current':
                inventory = product.mx_net_mrp_qty  # Current inv.
                # inventory = product.mx_lord_mrp_qty  # Current inv.
                if inventory <= 0:
                    without_inventory[product.id] = inventory
                    continue  # Written after in no inventory page!
            else:
                inventory = product.mx_start_qty  # Start inv.
            total = cost * inventory

            # Color setup:
            if cost:
                color_format = cell_format['text']
                color_number_format = cell_format['number']
            else:
                color_format = cell_format['bg']['red']
                color_number_format = cell_format['bg_number']['red']
                ws_names[category_name][2] += 1

            data = [
                product.default_code or '',
                product.name or '',
                product.uom_id.name or '',
                # product.statistic_category or '',
                # product.categ_id.name or '',
                supplier or '',
                (int(inventory), color_number_format),
                date or '',
                (int(number), color_number_format),
                (cost, color_number_format),
                (total, color_number_format),
                (standard_price, color_number_format),
                (weight, color_number_format),
                note or '',
                ]
            excel_pool.write_xls_line(
                category_name or ws_empty,
                ws_names[category_name][0],
                data,
                default_format=color_format,
                )
            ws_names[category_name][0] += 1
            ws_names[category_name][1] += total

        # ---------------------------------------------------------------------
        # Write empty page with no stock product:
        # ---------------------------------------------------------------------
        ws_page = 'Senza inventario'

        # Init setup:
        excel_pool.create_worksheet(ws_page)
        excel_pool.column_width(ws_page, [
            20, 15, 40, 5,
            8, 20, 10,
            ])
        excel_pool.write_xls_line(ws_page, 0, {
            'CAT. INV.', 'CODICE', 'DESCRIZIONE', 'UM',
            'CAT. STAT.', 'CATEGORIA', 'Q.',
            }, cell_format['header'])

        # Collect data:
        if mode == 'current':
            product_ids = without_inventory.keys()
        else:
            product_ids = product_pool.search(cr, uid, [
                ('mx_start_qty', '<=', 0.0),  # No inventory present
                ], context=context)

        row = 0
        for product in sorted(
                product_pool.browse(cr, uid, product_ids, context=context),
                key=lambda x: (
                    x.inventory_category_id.name,
                    x.default_code,
                    x.name,
                    )):
            row += 1
            excel_pool.write_xls_line(ws_page, row, [
                product.inventory_category_id.name,
                product.default_code,
                product.name,
                product.uom_id.name or '',
                product.statistic_category or '',
                product.categ_id.name or '',
                without_inventory.get(product.id, 0.0),
                ], cell_format['text'])

        # ---------------------------------------------------------------------
        # Write empty page with no stock product:
        # ---------------------------------------------------------------------
        ws_page = 'TOTALI'

        # Init setup:
        excel_pool.create_worksheet(ws_page)
        excel_pool.column_width(ws_page, [
            30, 5, 15,
            ])
        excel_pool.write_xls_line(ws_page, 0, [
            'Categorie', '# Err.', 'Totale',
            ], cell_format['header'])

        row = 1
        for category_name in sorted(ws_names):
            line, total, error = ws_names[category_name]
            if not category_name:
                continue

            excel_pool.write_xls_line(ws_page, row, [
                category_name,
                error,
                (total, cell_format['number']),
                ], cell_format['text'])
            row += 1

        # Generate attachment for return file:
        if mode == 'current':
            return excel_pool.return_attachment(
                cr, uid, 'inventario_attuale_magazzino', context=context)
        else:
            return excel_pool.return_attachment(
                cr, uid, 'inventario_inizio_anno', context=context)

    def extract_xls_table_inventory(
            self, cr, uid, ids, data=None, context=None):
        """ Extract table inventory:
        """
        product_pool = self.pool.get('product.product')
        excel_pool = self.pool.get('excel.writer')

        inventory_ids = data['inventory_ids']
        inventory_name = ', '.join(data['inventory_name'])

        # ---------------------------------------------------------------------
        #                              Excel report:
        # ---------------------------------------------------------------------
        # Create first populated after:
        WS_name = _('Stato piani tavoli')
        excel_pool.create_worksheet(WS_name)

        # ---------------------------------------------------------------------
        # Page table:
        # ---------------------------------------------------------------------
        WS_name = _('Elenco prodotti')
        excel_pool.create_worksheet(WS_name)

        # Load format used:
        excel_pool.set_format(number_format='#,##0.#0')
        format_mode = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),

            'text': {
                'white': excel_pool.get_format('text'),
                'red': excel_pool.get_format('bg_red'),
                'blue': excel_pool.get_format('bg_blue'),
                },
            'number': {
                'white': excel_pool.get_format('number'),
                'red': excel_pool.get_format('bg_red_number'),
                'blue': excel_pool.get_format('bg_blue_number'),
                },
            }
        now = datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT)

        # ---------------------------------------------------------------------
        # Collect data:
        # ---------------------------------------------------------------------
        product_ids = product_pool.search(cr, uid, [
            ('default_code', '=ilike', 'PIA%'), # Start with PIA
            ('inventory_category_id', 'in', inventory_ids), # Cat. selected.
            ], context=context)

        # ---------------------------------------------------------------------
        # Write file:
        # ---------------------------------------------------------------------
        # Cols setup:
        excel_pool.column_width(WS_name, [12, 40, 10])

        #`Header line:
        row = 0 # Start line
        excel_pool.write_xls_line(
            WS_name, row, ['Codice', 'Descrizione', 'Magazzino'],
            default_format=format_mode['header'])

        product_report = {}
        colors = []
        for product in product_pool.browse(cr, uid, product_ids,
                context=context):
            default_code = product.default_code or ''
            if len(default_code) in (8, 12):
                model = default_code[3:-2]
                color = default_code[-2:]
            elif len(default_code) in (9, 13):
                model = default_code[3:-3]
                color = default_code[-3:]
            else:
                _logger.error('Cannot locate color: %s' % default_code)
                continue

            if color not in colors:
                colors.append(color)
            if model not in product_report:
                product_report[model] = (product, {})
            qty = product.mx_net_mrp_qty
            product_report[model][1][color] = qty

            # Write summary page:
            row += 1
            excel_pool.write_xls_line(
                WS_name, row, [default_code, product.name, qty],
                format_mode['text']['white'])

        # ---------------------------------------------------------------------
        # Page table:
        # ---------------------------------------------------------------------
        WS_name = _('Stato piani tavoli')

        # ---------------------------------------------------------------------
        # Setup format:
        # ---------------------------------------------------------------------
        colors = sorted(colors)
        cols = len(colors)

        # Header setup:
        header = ['Modello', ] # Extra data: 'Codice', 'Descrizione',
        extra = len(header)
        header.extend([color.upper() for color in colors])

        # Cols setup:
        col_width = [7, ] # Extra data: 12, 35,
        col_width.extend([5 for item in range(0, cols)])
        excel_pool.column_width(WS_name, col_width)

        # ---------------------------------------------------------------------
        # Write file:
        # ---------------------------------------------------------------------
        #`Title line:
        row = 0 # Start line
        excel_pool.write_xls_line(
            WS_name, row, [
                'Stato magazzino piani tavoli al %s: %s' % (
                    now, inventory_name),
                ], default_format=format_mode['title'])

        # Header line:
        row += 2
        excel_pool.write_xls_line(
            WS_name, row, header, default_format=format_mode['header'])

        # Print Excel file
        for model in sorted(product_report):
            product = product_report[model][0]

            # Setup record to write:
            record = ['' for item in range(0, cols + extra)]
            # record[0] = product.default_code
            # record[1] = product.name
            record[0] = model

            for color in product_report[model][1]:
                qty = product_report[model][1][color]
                position = colors.index(color) + extra # TODO check!
                record[position] = (
                    str(int(qty)), format_mode['number']['white'])

            row += 1
            excel_pool.write_xls_line(
                WS_name, row, record,
                default_format=format_mode['text']['white'])

        return excel_pool.return_attachment(cr, uid, 'Stato piani')

    def extract_xls_inventory_file(
            self, cr, uid, ids, data=None,
            context=None):
        """ Extract inventory as XLS external files every category in different
            page
        """
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        def write_header(current_WS, header):
            """ Write header in first line:
            """
            col = 0
            for title in header:
                current_WS.write(0, col, title)
                col += 1
            return

        # ---------------------------------------------------------------------
        #                        XLS log export:
        # ---------------------------------------------------------------------
        # filename = '/home/administrator/photo/output/inventory_table.xlsx'
        dbname = cr.dbname.replace('.', '').replace('/', '').replace('\\', '')
        filename = os.path.join(
            os.path.expanduser('~/NAS/industria40/Report/Inventario'),
            'current_inventory_category_{}.xlsx'.format(dbname),
        )
        _logger.info('Sharepoint doc: {}'.format(filename))
        WB = xlsxwriter.Workbook(filename)

        # ---------------------------------------------------------------------
        # Search all inventory category:
        # ---------------------------------------------------------------------
        inv_pool = self.pool.get('product.product.inventory.category')
        inv_ids = inv_pool.search(cr, uid, [], context=context)

        # ---------------------------------------------------------------------
        # Create work sheet:
        # ---------------------------------------------------------------------
        header = ['DB', 'CODICE', 'DESCRIZIONE', 'UM', 'CAT. STAT.',
            'CATEGORIA', 'FORNITORE', 'NETTO', 'LORDO',
            'INV', 'INV. DELTA', 'MRP', 'ESISTENZA']

        # Create element for empty category:
        WS = {
            # ID: worksheet, counter
            0: [WB.add_worksheet('Non assegnati'), 1],
            }
        write_header(WS[0][0], header)

        # Create all others category:
        for category in inv_pool.browse(
                cr, uid, inv_ids, context=context):
            WS[category.id] = [WB.add_worksheet(category.name), 1]
            write_header(WS[category.id][0], header)

        # ---------------------------------------------------------------------
        # Prepare BOM check
        # ---------------------------------------------------------------------
        # TODO check if there's production mode:
        line_pool = self.pool.get('mrp.bom.line')
        line_ids = line_pool.search(cr, uid, [
            ('bom_id.bom_category', 'in', ('parent', 'dynamic', 'half')),
            ], context=context)

        in_bom_ids = [item.product_id.id for item in line_pool.browse(
            cr, uid, line_ids, context=context)]

        # TODO remove after print:
        with_parent_bom = False
        linked_bom = {}
        if with_parent_bom:
            linked_bom_ids = line_pool.search(cr, uid, [
                ('bom_id.bom_category', '=', 'parent'),
                ], context=context)
            for line in line_pool.browse(cr, uid, linked_bom_ids,
                    context=context):
                linked_bom[
                    line.product_id.id] = line.bom_id.product_id.default_code

        # ---------------------------------------------------------------------
        # Populate product in correct page
        # ---------------------------------------------------------------------
        for product in self.pool.get(
                'product.product').stock_status_report_get_object(
                    cr, uid, data=data, context=context):
            if product.inventory_category_id.id in WS:
                record = WS[product.inventory_category_id.id]
            else:
                record = WS[0]

            # Write data in correct WS:
            record[0].write(record[1], 0,
                'X' if product.id in in_bom_ids else '')
            record[0].write(record[1], 1, product.default_code)
            record[0].write(record[1], 2, product.name)
            record[0].write(record[1], 3, product.uom_id.name or '')
            record[0].write(record[1], 4, product.statistic_category or '')
            record[0].write(record[1], 5, product.categ_id.name or '')
            record[0].write(record[1], 6,
                product.seller_ids[0].name.name if product.seller_ids else (
                    product.first_supplier_id.name or ''))

            # Weight:
            record[0].write(record[1], 7, product.weight_net)
            record[0].write(record[1], 8, product.weight)

            if data.get('with_stock', False):
                net_qty = product.mx_net_qty - product.mx_mrp_out
                record[0].write(record[1], 9, product.inventory_start or '')
                record[0].write(record[1], 10, product.inventory_delta or '')
                record[0].write(record[1], 11, product.mx_mrp_out or '')
                record[0].write(record[1], 12, net_qty or '')

            # TODO remove after print:
            if with_parent_bom:
                record[0].write(record[1], 13, linked_bom.get(product.id, ''))

            record[1] += 1
        return True

    # -------------------------------------------------------------------------
    #                             Wizard button event
    # -------------------------------------------------------------------------
    def get_data_dict(self, wiz_proxy):
        """ Utility for create data dict in report actions
        """
        datas = {
            'wizard': True, # started from wizard
            'partner_id': wiz_proxy.partner_id.id,
            'partner_name': wiz_proxy.partner_id.name,
            'default_code': wiz_proxy.default_code or False,
            'categ_ids': [item.id for item in wiz_proxy.categ_ids],
            'categ_name': [item.name for item in wiz_proxy.categ_ids],
            'catalog_ids': [item.id for item in wiz_proxy.catalog_ids],
            'catalog_name': [item.name for item in wiz_proxy.catalog_ids],
            'status': wiz_proxy.status or False,
            'sortable': wiz_proxy.sortable or False,
            'mode': wiz_proxy.mode or False,
            'with_photo': wiz_proxy.with_photo,
            'with_stock': wiz_proxy.with_stock,
            'inventory_category_id': wiz_proxy.inventory_category_id.id,
            'inventory_ids': [item.id for item in wiz_proxy.inventory_ids],
            'inventory_name': [item.name for item in wiz_proxy.inventory_ids],
            }

        if wiz_proxy.statistic_category:
            datas['statistic_category'] = [
                item.strip() for item in (
                    wiz_proxy.statistic_category or '').split('|')]
        else:
            datas['statistic_category'] = False
        return datas

    def extract_corresponding(
            self, cr, uid, ids, wiz_proxy, context=None):
        """ Extract corresponding
        """
        # Pool used:
        move_pool = self.pool.get('stock.move')
        excel_pool = self.pool.get('excel.writer')

        # =====================================================================
        #                       GENERATE DOMAIN FILTER:
        # =====================================================================
        filter_text = u'Movimenti di corrispettivo: '

        # Read wizard data:
        partner = wiz_proxy.customer_id
        destination = wiz_proxy.destination_partner_id

        from_date = wiz_proxy.from_date
        to_date = wiz_proxy.to_date

        # ---------------------------------------------------------------------
        # Date filter
        # ---------------------------------------------------------------------
        domain = [
            ('picking_id.correspond', '=', True),
        ]
        if partner:
            domain.append(('picking_id.partner_id', '=', partner.id))
            filter_text += 'Partner %s ' % partner.name
        if destination:
            domain.append(
                ('picking_id.destination_partner_id', '=', destination.id))
            filter_text += 'Destinazione %s ' % destination.name
        if from_date:
            domain.append(('picking_id.date', '>=', '%s 00:00:00' % from_date))
            filter_text += 'Dalla data %s ' % from_date
        if to_date:
            domain.append(('picking_id.date', '<=', '%s 23:59:59' % to_date))
            filter_text += 'Alla data %s ' % to_date

        move_ids = move_pool.search(cr, uid, domain, context=context)
        moves = move_pool.browse(cr, uid, move_ids, context=context)

        # ---------------------------------------------------------------------
        #                            Excel export:
        # ---------------------------------------------------------------------
        ws_name = u'Magazzino disponibile'
        excel_pool.create_worksheet(ws_name)
        excel_pool.column_width(ws_name, [
            20, 20,
            35, 35,
            15, 15, 50, 10,
        ])
        excel_pool.set_format()
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_number = excel_pool.get_format('number')

        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            u'Filtro: %s' % filter_text,
        ], f_title)

        row += 1
        excel_pool.write_xls_line(ws_name, row, [
            u'Doc. origine', u'Doc. scarico',
            u'Partner', u'Destinazione',
            u'Data', u'Codice', u'Descrizione', u'Q.tà',
        ], f_header)

        for move in moves:
            row += 1
            picking = move.picking_id
            product = move.product_id
            excel_pool.write_xls_line(ws_name, row, [
                picking.origin or '',
                picking.name,
                picking.partner_id.name,
                picking.destination_partner_id.name or '',
                picking.date[:10],
                product.default_code or '?',
                product.name,
                (move.product_qty, f_number),
            ], f_text)

        return excel_pool.return_attachment(
            cr, uid, 'corrispettivi_magazzino', context=context)

    def extract_available_stock_status(
            self, cr, uid, ids, wiz_proxy, context=None):
        """ Extract available status for stock
        """
        # Pool used:
        partner_pool = self.pool.get('res.partner')
        product_pool = self.pool.get('product.product')
        supplier_pool = self.pool.get('product.supplierinfo')
        excel_pool = self.pool.get('excel.writer')

        # =====================================================================
        #                       GENERATE DOMAIN FILTER:
        # =====================================================================
        product_ids = []
        filter_text = u'Prodotti con disponibilità'

        # Read wizard data:
        partner_id = wiz_proxy.partner_id.id
        default_code = wiz_proxy.default_code
        statistic_category = wiz_proxy.statistic_category
        categ_ids = wiz_proxy.categ_ids
        catalog_ids = wiz_proxy.catalog_ids
        status = wiz_proxy.status # gamma
        sortable = wiz_proxy.sortable
        inventory_category_id = wiz_proxy.inventory_category_id.id

        # ---------------------------------------------------------------------
        # SUPPLIER FILTER:
        # ---------------------------------------------------------------------
        if partner_id:
            filter_text += u', con partner: %s' % wiz_proxy.partner_id.name
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
            filter_text += u', con codice: %s' % default_code

        if statistic_category:
            domain.append(
                ('statistic_category', 'in', statistic_category.split('|')))
            filter_text += \
                u', con categoria statistica: %s' % statistic_category

        if categ_ids:
            domain.append(('categ_id', 'in', categ_ids))
            filter_text += u', con categorie in: %s' % categ_ids

        if catalog_ids: # TODO test
            domain.append(('catalog_ids', 'in', catalog_ids))
            filter_text += u', con catalogo: %s' % catalog_ids

        if status:
            domain.append(('status', '=', status))
            filter_text += u', con gamma: %s' % status

        if sortable:
            domain.append(('sortable', '=', True))
            filter_text += u', ordinabile'

        if inventory_category_id:
            domain.append(
                ('inventory_category_id', '=', inventory_category_id))
            filter_text += u', con categoria inventario: %s' % \
                wiz_proxy.inventory_category_id.name

        product_ids = product_pool.search(cr, uid, domain, context=context)
        products = product_pool.browse(cr, uid, product_ids, context=context)

        # ---------------------------------------------------------------------
        #                            Excel export:
        # ---------------------------------------------------------------------
        ws_name = u'Magazzino disponibile'
        excel_pool.create_worksheet(ws_name)
        excel_pool.column_width(ws_name, [
            20,
            40,
            15,
            20,
            15,
            10,
            10,
            ])
        excel_pool.set_format()

        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_number = excel_pool.get_format('number')

        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            'Filtro: %s' % filter_text,
            ], f_title)

        row += 1
        excel_pool.write_xls_line(ws_name, row, [
            u'Codice',
            u'Descrizione',
            u'Cat. Stat.',
            u'Cat invent.',
            u'Gamma',
            u'Magazzino',
            u'Disponibile'
            ], f_header)

        for product in products:
            stock_net = product.mx_net_mrp_qty
            stock_locked = product.mx_mrp_b_locked
            stock_available = stock_net - stock_locked
            if stock_available <= 0:
                continue # Jumped product

            row += 1
            excel_pool.write_xls_line(ws_name, row, [
                product.default_code or '?',
                product.name,
                product.statistic_category or '',
                product.inventory_category_id.name or '',
                product.status,
                (stock_net, f_number),
                (stock_available, f_number),
                ], f_text)

        return excel_pool.return_attachment(
            cr, uid, 'disponibili_magazzino', context=context)

    def print_report(self, cr, uid, ids, context=None):
        """ Print report product
        """
        if context is None:
            context = {}

        wiz_proxy = self.browse(cr, uid, ids)[0]
        datas = self.get_data_dict(wiz_proxy)

        if datas['mode'] == 'status':
            report_name = 'stock_status_report'
        elif datas['mode'] == 'simple':
            report_name = 'stock_status_simple_report'
        elif datas['mode'] == 'inventory':
            # XXX Migrate in Excel:
            # report_name = 'stock_status_inventory_report'
            return self.extract_stock_status_xls_inventory_file(
                cr, uid, ids, datas, context=context)

        elif datas['mode'] == 'table':
            return self.extract_xls_table_inventory(
                cr, uid, ids, datas, context=context)

        elif datas['mode'] == 'inventory_xls':
            return self.extract_xls_inventory_file(
                cr, uid, ids, datas, context=context)
        elif datas['mode'] == 'inventory_check_xls':
            return self.extract_xls_check_inventory_file(
                cr, uid, ids, datas, context=context)
        elif datas['mode'] == 'inventory_old_xls':
            return self.extract_old_xls_inventory_file(
                cr, uid, ids, datas, context=context)
        elif datas['mode'] == 'available':
            return self.extract_available_stock_status(
                cr, uid, ids, wiz_proxy, context=context)
        elif datas['mode'] == 'corresponding':
            return self.extract_corresponding(
                cr, uid, ids, wiz_proxy, context=context)
        # elif datas['mode'] == 'inventory_web':
        #    return self.extract_web_inventory_file(
        #        cr, uid, ids, datas, context=context)
        else:
            raise osv.except_osv(
                _('No type'),
                _('Check type setup (not present)'),
                )

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            }

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier',
            domain=[
                ('supplier', '=', True),
                ('is_company', '=', True),
                ('is_address', '=', False),
                ]),
        'customer_id': fields.many2one(
            'res.partner', 'Cliente',
            domain=[
                ('is_company', '=', True),
                ('is_address', '=', False),
                ]),
        'destination_partner_id': fields.many2one(
            'res.partner', 'Destinazione',
            domain="[('is_address', '=', True), "
                   "('parent_id', '=', customer_id)]"),
        'from_date': fields.date('Dalla data'),
        'to_date': fields.date('Alla data'),
        'default_code': fields.char('Partial code', size=30),
        'statistic_category': fields.char('Statistic category (separ.: |)',
            size=50),
        'inventory_ids': fields.many2many(
            'product.product.inventory.category', 'product_wiz_inv_cat_rel',
            'wizard_id', 'inventory_id',
            'Categorie inventario'),
        'categ_ids': fields.many2many(
            'product.category', 'product_category_status_rel',
            'product_id', 'category_id',
            'Category'),
        'catalog_ids': fields.many2many(
            'product.product.catalog', 'product_catalog_status_rel',
            'product_id', 'catalog_id',
            'Catalog'),
        'inventory_category_id': fields.many2one(
            'product.product.inventory.category', 'Inventory category'),
        'status': fields.selection([
            ('catalog', 'Catalog'),
            ('out', 'Out catalog'),
            ('stock', 'Stock'),
            ('obsolete', 'Obsolete'),
            ('sample', 'Sample'),
            ('promo', 'Promo'),
            ('parent', 'Padre'),
            ('todo', 'Todo'),
            ], 'Gamma'),
        'sortable': fields.boolean('Sortable'),
        'with_photo': fields.boolean('With photo'),
        'with_stock': fields.boolean('With stock'),
        'mode': fields.selection([
            ('status', 'Stock status'),
            ('simple', 'Simple status'),
            ('inventory', 'Inventory'),
            ('table', 'Inventario tavoli'),
            ('inventory_xls', 'Inventario per categoria XLSX (Sharepoint)'),
            ('inventory_check_xls', 'Inventory check XLS (exported not report)'),
            ('inventory_old_xls', 'Inventario precedente valorizzato'),
            ('available', 'Disponibile (non collegato a ordini)'),
            ('corresponding', 'Scaricato con corrispettivo'),
            ], 'Mode', required=True)
        }

    _defaults = {
        'with_photo': lambda *x: True,
        'mode': lambda *x: 'status',
        }
