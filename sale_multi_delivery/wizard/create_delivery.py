# -*- coding: utf-8 -*-
###############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import xlrd
import logging
import base64
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)

_logger = logging.getLogger(__name__)


class CreateSaleOrderDeliveryWizard(orm.TransientModel):
    """ Create delivery order from sale order
    """
    _name = 'create.sale.order.delivery.wizard'

    # --------------
    # Wizard button:
    # --------------
    def import_load_delivery_file(self, cr, uid, ids, context=None):
        """ Import file and create order delivery
        """
        # Pool used:
        order_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')
        delivery_id = ids[0]

        wizard = self.browse(cr, uid, delivery_id, context=context)
        if wizard.order_ids:
            raise osv.except_osv(
                _('Errore'),
                _(u'Questa consegna ha già dei documenti collegati, partire da'
                  u' una vuota!'),
                )
        if wizard.file:
            raise osv.except_osv(
                _('Errore'),
                _(u'Caricare prima il file qui a sinistra!'),
                )

        # Load and save Excel file:
        b64_file = base64.decodestring(wizard.file)
        now = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        filename = '/tmp/delivery_%s.xlsx' % now.replace(
            ':', '_').replace('-', '_')
        f = open(filename, 'wb')
        f.write(b64_file)
        f.close()

        # ---------------------------------------------------------------------
        # Load force name (for web publish)
        # ---------------------------------------------------------------------
        try:
            wb = xlrd.open_workbook(filename)
        except:
            raise osv.except_osv(
                _('Error XLSX'),
                _('Cannot read XLS file: %s' % filename),
                )

        # ---------------------------------------------------------------------
        # Read Excel file
        # ---------------------------------------------------------------------
        ws = wb.sheet_by_index(0)
        _logger.warning('Read first page')
        import pdb; pdb.set_trace()

        linked_ids = []
        partner_id = False
        start = False
        result = {
            'error': '',
            'warning': '',
            'info': '',
        }

        for row in range(ws.nrows):
            human_row = row + 1
            # Check if start:
            if not start:
                if ws.cell(row, 0).value == 'START':
                    start = True
                    for col in range(ws.ncols):
                        ws.cell(row, col).value == 'QUANTITY'
                        quantity_col = col
                        break
                    if not quantity_col:
                        raise osv.except_osv(
                            _('Errore'),
                            _(u'Colonna scarico merce non trovata!'),
                        )
                continue

            # Read data:
            line_id = ws.cell(row, 0).value
            quantity = ws.cell(row, quantity_col).value

            # -----------------------------------------------------------------
            # Check data:
            # -----------------------------------------------------------------
            # a. Quantity positive:
            if not quantity:
                result['info'] += u'%s. Riga senza quantità' % human_row
                continue
            if quantity < 0:
                result['info'] += u'%s. Riga con q. negativa!' % human_row
                continue

            # b. ID row not found:
            try:
                line = line_pool.browse(cr, uid, line_id, context=context)
            except:
                result['error'] += '%s. ID riga non trovato!' % (row + 1)
                raise osv.except_osv(
                    _('Errore'),
                    _(u'ID riga non trovata!'),
                )

            # c. Check available:
            available = (line.product_uom_maked_sync_qty + line.mx_assigned_qty
                         - line.delivered_qty)
            if quantity > available:
                if available:
                    result['warning'] += \
                        '%s. Q. %s > %s (disponibile) preso la disponibile' % (
                            human_row, quantity, available)
                    quantity = available
                else:
                    result['error'] += u'%s. Tutto già consegnato!'
                    continue

            # d. Check partner
            order_partner_id = line.order_id.partner_id
            if partner_id:
                if partner_id != order_partner_id:
                    raise osv.except_osv(
                        _('Error XLSX'),
                        _('Partner differenti negli ordini collegati!'),
                    )
            else:  # Update multi delivery partner
                partner_id = order_partner_id
                self.write(cr, uid, [delivery_id], {
                    'partner_id': partner_id,
                    'note': 'Importato da file di consegna',
                }, context=context)

            # -----------------------------------------------------------------
            # Generate delivery data:
            # -----------------------------------------------------------------
            # a. Link order to delivery:
            order = line.order_id
            order_id = order.id
            if order_id not in linked_ids:
                linked_ids.append(order_id)
                order_pool.write(cr, uid, [order_id], {
                    'multi_delivery_id': delivery_id,
                }, context=context)

            # b. Link sale line q.
            line_pool.write(cr, uid, [line_id], {
                'multi_delivery_id': delivery_id,  # TODO only this line?
                'to_delivery_qty': quantity,
            }, context=context)
        return True

    def action_create_delivery_order(self, cr, uid, ids, context=None):
        """ Create delivery order from sale
        """
        if context is None:
            context = {}

        # Wizard proxy:
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]

        # Pool used:
        delivery_pool = self.pool.get('sale.order.delivery')
        sale_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')

        # ---------------------------------------------------------------------
        #                               HEADER PART
        # ---------------------------------------------------------------------
        sale_ids = context.get('active_ids', False)
        partner_id = False
        active_order_ids = []
        for sale in sale_pool.browse(cr, uid, sale_ids, context=context):
            if sale.mx_closed:
                continue  # jump order
            if not partner_id:
                partner_id = sale.partner_id.id
            if partner_id != sale.partner_id.id:
                raise osv.except_osv(
                    _('Error'),
                    _('Delivery order must have order with same partner'),
                )
            active_order_ids.append(sale.id)

        delivery_id = delivery_pool.create(cr, uid, {
            'partner_id': partner_id,
            'note': wiz_proxy.note,
            }, context=context)

        # Assign order to delivery:
        sale_pool.write(cr, uid, active_order_ids, {
            'multi_delivery_id': delivery_id,
            }, context=context)

        # ---------------------------------------------------------------------
        #                               LINE PART
        # ---------------------------------------------------------------------
        line_ids = line_pool.search(cr, uid, [
            ('order_id', 'in', active_order_ids)], context=context)
        # Reset data for link to new delivery obj
        line_pool.write(cr, uid, line_ids, {
            'to_deliver_qty': 0.0,
            'multi_delivery_id': False,
            }, context=context)
        remain_ids = []
        for line in line_pool.browse(cr, uid, line_ids, context=context):
            if line.product_uom_qty > line.delivered_qty:
                remain_ids.append(line.id)

        # Update only line with remain q.ty
        line_pool.write(cr, uid, remain_ids, {
            'multi_delivery_id': delivery_id,
            }, context=context)

        return {
            'view_type': 'form',
            'view_mode': 'form', # ,tree',
            'res_model': 'sale.order.delivery',
            # 'views': views,
            # 'domain': [('id', '=', delivery_id)],
            # 'views': [(view_id, 'form')],
            # 'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            # 'target': 'new',
            'res_id': delivery_id,
            }

    # -----------------
    # Default function:
    # -----------------
    def default_error(self, cr, uid, context=None):
        """ Check that order has all same partner
        """
        sale_pool = self.pool.get('sale.order')
        sale_ids = context.get('active_ids', False)
        partner_id = False
        for sale in sale_pool.browse(cr, uid, sale_ids, context=context):
            if partner_id == False:
                partner_id = sale.partner_id.id
            if partner_id != sale.partner_id.id:
                return 'Delivery order must have order with same partner'
                # raise osv.except_osv(
                #    _('Error'),
                #    _('Delivery order must have order with same partner'
                #    ))
        return False

    def default_oc_list(self, cr, uid, context=None):
        """ Show in html order list
        """
        if context is None:
            context = {}

        sale_pool = self.pool.get('sale.order')
        sale_ids = context.get('active_ids', [])
        res = """
                <style>
                    .table_bf {
                         border: 1px solid black;
                         padding: 3px;
                     }
                    .table_bf td {
                         border: 1px solid black;
                         padding: 3px;
                         text-align: center;
                     }
                    .table_bf th {
                         border: 1px solid black;
                         padding: 3px;
                         text-align: center;
                         background-color: grey;
                         color: white;
                     }
                </style>
                <table class='table_bf'>
                <tr class='table_bf'>
                    <th>OC</th>
                    <th>Partner</th>
                    <th>Date</th>
                </tr>"""

        for order in sale_pool.browse(cr, uid, sale_ids, context=context):
            res += """
                <tr>
                    <td>%s</td>
                    <td>%s</td>
                    <td>%s</td>
                </tr>""" % (
                    order.name,
                    order.partner_id.name,
                    order.date_order,
                    )
        res += "</table>"  # close table for list element
        return res

    _columns = {
        'note': fields.text('Note'),
        'error': fields.text('Error', readonly=True),
        'order_list': fields.text('Order list', readonly=True),
        'file': fields.binary('XLSX file', filters=None),
        }

    _defaults = {
        'error': lambda s, cr, uid, c: s.default_error(
            cr, uid, context=c),
        'order_list': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, context=c),
         }
