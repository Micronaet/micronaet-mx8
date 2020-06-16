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
import base64
import xlrd
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


class SaleOrderDelivery(orm.Model):
    """ Model name: SaleOrderDelivery
    """
    _name = 'sale.order.delivery'
    _description = 'Sale order delivery'
    _order = 'create_date desc'

    def import_load_delivery_file(self, cr, uid, ids, context=None):
        """ Import file and create order delivery
        """
        # Pool used:
        order_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')
        delivery_id = ids[0]
        import pdb; pdb.set_trace()

        delivery = self.browse(cr, uid, delivery_id, context=context)
        if delivery.order_ids:
            raise osv.except_osv(
                _('Errore'),
                _(u'Questa consegna ha già dei documenti collegati, partire da'
                  u' una vuota!'),
                )
        if delivery.file:
            raise osv.except_osv(
                _('Errore'),
                _(u'Caricare prima il file qui a sinistra!'),
                )

        # Load and save Excel file:
        b64_file = base64.decodestring(delivery.file)
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
                    # 'create_date'
                    # 'create_uid'
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

    def button_open_all_picking(self, cr, uid, ids, context=None):
        """ Open order
        """
        assert len(ids) == 1, 'Button work only with one record a time!'
        context = context or {}

        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        pick_ids = [item.id for item in current_proxy.picking_ids]

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            # 'views': views,
            'domain': [('id', '=', pick_ids)],
            # 'views': [(view_id, 'form')],
            # 'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            # 'target': 'new',
            # 'res_id': ids[0],
            }

    # Button create picking:
    def action_delivery(self, cr, uid, ids, context=None):
        """ Event for button done the delivery
        """
        assert len(ids) == 1, 'Button work only with one record a time!'
        context = context or {}

        current_proxy = self.browse(cr, uid, ids, context=context)[0]

        # Pool used:
        line_pool = self.pool.get('sale.order.line')
        move_pool = self.pool.get('stock.move')
        picking_pool = self.pool.get('stock.picking')
        type_pool = self.pool.get('stock.picking.type')

        wf_service = netsvc.LocalService('workflow')  # TODO deprecated!

        # Parameters:
        type_ids = type_pool.search(cr, uid, [
            ('code', '=', 'outgoing')], context=context)
        if not type_ids:
            _logger.error('Type outgoing not found')
            return
        type_id = type_ids[0]
        type_proxy = type_pool.browse(
            cr, uid, type_id, context=context)

        date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        pickings = {}
        for sale in current_proxy.order_ids:
            picking_id = False # for WF action
            for line in sale.order_line:
                if line.product_id.type not in ('product', 'consu'):  # service
                    # TODO log error
                    continue

                if not line.product_id:
                    # TODO log error
                    continue

                if not line.to_deliver_qty:
                    continue  # jump line

                # -------------------------------------------------------------
                #                           PICKING
                # -------------------------------------------------------------
                if sale.id not in pickings:
                    # Create pick:
                    pickings[sale.id] = picking_pool.create(cr, uid, {
                        # -------------------------------------------------
                        #                 Default elements:
                        # -------------------------------------------------
                        'name': self.pool.get('ir.sequence').get(
                            cr, uid, 'stock.picking.out'),
                        'origin': sale.name,
                        'date': date,
                        # 'type': 'out',
                        'picking_type_id': type_id,
                        'state': 'done', # TODO removed: 'auto',
                        'move_type': sale.picking_policy,

                        # TODO create using group_id instead of sale_id
                        'group_id': sale.procurement_group_id.id,
                        'sale_id': sale.id, # TODO no more used!

                        # Partner in cascade assignment:
                        'partner_id': sale.partner_id.id or \
                            sale.address_id.id or sale.partner_shipping_id.id,
                        'note': sale.note,
                        'invoice_state': '2binvoiced' if \
                            sale.order_policy=='picking' else 'none',
                        'company_id': sale.company_id.id,

                        # -------------------------------------------------
                        #                 Extra elements:
                        # -------------------------------------------------
                        # TODO vector and others needed!
                        'multi_delivery_id': ids[0],
                        'mx_agent_id': sale.mx_agent_id.id,
                        'transportation_reason_id':
                            sale.transportation_reason_id.id,
                        'goods_description_id':
                            sale.goods_description_id.id,
                        'carriage_condition_id':
                            sale.carriage_condition_id.id,

                        # Partner ref.:
                        'destination_partner_id':
                            sale.destination_partner_id.id,
                        'invoice_partner_id':
                            sale.invoice_partner_id.id,
                        'text_note_pre': sale.text_note_pre,
                        'text_note_post': sale.text_note_post,
                        }, context=context)

                # -------------------------------------------------------------
                #                           STOCK MOVE
                # -------------------------------------------------------------
                picking_id = pickings[sale.id]
                location_id = type_proxy.default_location_src_id.id
                output_id = type_proxy.default_location_dest_id.id
                to_deliver_qty = line.to_deliver_qty # TODO change!!!!!!!!!!!!!

                data_move = {
                    # ---------------------------------------------------------
                    #                   Default data:
                    # ---------------------------------------------------------
                    'name': line.name,
                    'picking_id': picking_id,
                    'product_id': line.product_id.id,
                    'date': date,#_planned,
                    'date_expected': date,#_planned,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'product_uos_qty': (
                        line.product_uos and line.product_uos_qty) or \
                            line.product_uom_qty,
                    'product_uos': (
                        line.product_uos and line.product_uos.id)\
                            or line.product_uom.id,
                    'product_packaging': line.product_packaging.id,
                    'partner_id': line.address_allotment_id.id or \
                        sale.partner_shipping_id.id,
                    'location_id': location_id,
                    'location_dest_id': output_id,
                    'sale_line_id': line.id,
                    'company_id': sale.company_id.id,
                    'price_unit': line.product_id.standard_price or 0.0,
                    # 'tracking_id': False,
                    # 'state': 'waiting',

                    # ---------------------------------------------------------
                    #                   Extra data:
                    # ---------------------------------------------------------
                    'product_uos_qty': to_deliver_qty,
                    'product_uom_qty': to_deliver_qty,
                    # TODO discount

                    'state': 'assigned',
                    'invoice_state': '2binvoiced',

                    # OC Field to move on:
                    'use_text_description': line.use_text_description,
                    'text_note_pre': line.text_note_pre,
                    'text_note_post': line.text_note_post,
                    }
                move_pool.create(
                    cr, uid, data_move, context=context)

            # Confirm workflow for picking:
            if picking_id:
                wf_service.trg_validate(
                    uid, 'stock.picking', picking_id, 'button_confirm', cr)

        self.write(cr, uid, ids, {
            'state': 'done', }, context=context)
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            # 'views': views,
            'domain': [('id', '=', pickings.values())],
            # 'views': [(view_id, 'form')],
            # 'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            # 'target': 'new',
            # 'res_id': delivery_id,
            }

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'create_date': fields.date('Create date', readonly=True),
        'create_uid': fields.many2one('res.users', 'Create user',
            readonly=True),
        'file': fields.binary('XLSX file', filters=None),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'note': fields.text('Note'),
        'state': fields.selection([
            ('draft', 'Draft'), ('done', 'Done'),
            ], 'State', readonly=True),
        }

    _defaults = {
        'name': lambda *a: _('Multi delivery of: %s' % (
            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))),
        'state': lambda *x: 'draft',
        }


class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'sale.order'

    def button_open_order(self, cr, uid, ids, context=None):
        """ Open order
        """
        return {
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'sale.order',
            # 'views': views,
            # 'domain': [('id', '=', pickings.values())],
            # 'views': [(view_id, 'form')],
            # 'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            # 'target': 'new',
            'res_id': ids[0],
            }

    _columns = {
        'multi_delivery_id': fields.many2one(
            'sale.order.delivery', 'Multi delivery', ondelete='set null'),
        }


class StockPicking(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'stock.picking'

    def button_open_ddt(self, cr, uid, ids, context=None):
        """ Open order
        """
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        if not current_proxy.ddt_id.id:
            return True

        return {
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'stock.ddt',
            #'views': views,
            #'domain': [('id', '=', pickings.values())],
            #'views': [(view_id, 'form')],
            #'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': current_proxy.ddt_id.id,
            }

    def button_open_invoice(self, cr, uid, ids, context=None):
        """ Open order
        """
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        if not current_proxy.invoice_id.id:
            return True

        return {
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            #'views': views,
            #'domain': [('id', '=', pickings.values())],
            #'views': [(view_id, 'form')],
            #'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': current_proxy.invoice_id.id,
            }

    # TODO needed?!?!
    def button_open_order(self, cr, uid, ids, context=None):
        """ Open order
        """
        return {
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'stock.picking',
            #'views': views,
            #'domain': [('id', '=', ids)],
            #'views': [(view_id, 'form')],
            #'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': ids[0],
            }
    def button_open_picking(self, cr, uid, ids, context=None):
        """ Open order
        """
        return {
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'stock.picking',
            #'views': views,
            #'domain': [('id', '=', ids)],
            #'views': [(view_id, 'form')],
            #'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': ids[0],
            }

    _columns = {
        'multi_delivery_id': fields.many2one(
            'sale.order.delivery', 'Multi delivery', ondelete='set null'),
        }


class SaleOrderLine(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'sale.order.line'

    def nothing(self, cr, uid, ids, context=None):
        return True

    def set_zero_qty(self, cr, uid, ids, context=None):
        """ Set 0
        """
        assert len(ids) == 1, 'Only one line a time'

        line_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.write(cr, uid, ids, {
            'to_deliver_qty': 0.0,
            }, context=context)

    def set_all_qty(self, cr, uid, ids, context=None):
        """ Set qty depend on remain (overridable from MRP!!!)
        """
        assert len(ids) == 1, 'Only one line a time'

        line_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.write(cr, uid, ids, {
            'to_deliver_qty':
                line_proxy.product_uom_qty - line_proxy.delivered_qty,
            }, context=context)

    # def _get_move_lines(self, cr, uid, ids, context=None):
    #    ''' When change ref. in order also in lines
    #    '''
    #    sale_pool = self.pool['sale.order']
    #    res = []
    #    for sale in sale_pool.browse(cr, uid, ids, context=context):
    #        for line in sale.order_line:
    #            res.append(line.id)
    #    return res

    # def _get_move_line_lines(self, cr, uid, ids, context=None):
    #    ''' When change ref. in order also in lines
    #    '''
    #    return ids

    _columns = {
        'to_deliver_qty': fields.float('To deliver', digits=(16, 2)),
        'multi_delivery_id': fields.many2one(
            'sale.order.delivery', 'Multi delivery', ondelete='set null'),

        # 'multi_delivery_id': fields.related(
        #    'order_id', 'multi_delivery_id',
        #    type='many2one', relation='sale.order.delivery',
        #    string='Multi delivery', store={
        #        # Auto change if moved line in other order:
        #        #'sale.order.line': (
        #        #    lambda s, cr, uid, ids, c: ids,
        #        #    ['order_id'],
        #        #    10),
        #        # Wneh change in order header value:
        #        'sale.order': (
        #            _get_move_lines, ['multi_delivery_id'], 10),
        #        'sale.order.line': (
        #            _get_move_line_lines, ['order_id'], 10),
        #        }),
        }


class SaleOrderDelivery(orm.Model):
    """ Model name: SaleOrderDelivery for 2many elements
    """
    _inherit = 'sale.order.delivery'

    _columns = {
        'order_ids': fields.one2many('sale.order', 'multi_delivery_id',
            'Order'),
        'picking_ids': fields.one2many('stock.picking', 'multi_delivery_id',
            'Picking'),
        'line_ids': fields.one2many('sale.order.line', 'multi_delivery_id',
            'Lines'),
        }
