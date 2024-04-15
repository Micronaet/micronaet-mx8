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


class AssignStockToOrderWizard(orm.TransientModel):
    """ Assign stock with order Wizard
    """
    _name = 'assign.stock.to.order.wizard'

    # --------------
    # Wizard button:
    # --------------
    def action_assign_stock(self, cr, uid, ids, context=None):
        """ Create delivery order from sale
        """
        order_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')

        if context is None:
            context = {}

        # Wizard proxy:
        wizard = self.browse(cr, uid, ids, context=context)[0]
        order_id = wizard.order_id.id

        chat_message = ''
        for line in wizard.line_ids:
            warning = ''
            sale_line = line.line_id
            line_id = sale_line.id
            if not line_id:
                continue

            product = sale_line.product_id
            default_code = product.default_code or product.name

            oc_qty = line.oc_qty
            available_qty = line.available_qty
            assigned_qty = line.assigned_qty
            this_assign_qty = line.this_assign_qty

            # -----------------------------------------------------------------
            # Check data:
            # -----------------------------------------------------------------
            # 1. Over available
            # todo (complicazione con già assegnato)

            # 2. Same assigned no modify:
            if assigned_qty == this_assign_qty:
                _logger.warning('No change in assigned qty')
                warning += \
                    '[Stessa assegnazione, nessuna modifica] '

            # 3. Over order:
            elif this_assign_qty > oc_qty:
                _logger.warning('No assigned over order')
                warning += \
                    '[Assegnato oltre OC corretto q.] '
                this_assign_qty = oc_qty

            # 4. Update:
            line_pool.write(cr, uid, [line_id], {
                'mx_assigned_qty': this_assign_qty,
            }, context=context)

            chat_message += \
                '[INFO] {} Assegnato magazzino per q. {} (prec. {}) ' \
                '[Dispo mag: {}] {}\n'.format(
                    default_code,
                    this_assign_qty,
                    assigned_qty,
                    available_qty,
                    warning
                )

        # Write log message:
        return order_pool.message_post(
            cr, uid, [order_id],
            body=chat_message.replace('\n', '<br/>'),
            context=context)

    _columns = {
        'order_id': fields.many2one('sale.order', 'Ordine')
        }


class AssignStockToOrderLineWizard(orm.TransientModel):
    """ Assign stock with order Wizard Line
    """
    _name = 'assign.stock.to.order.line.wizard'

    _columns = {
        'wizard_id': fields.many2one(
            'assign.stock.to.order.wizard', 'Wizard'),
        'line_id': fields.many2one('sale.order.line', 'Riga'),

        'oc_qty': fields.float('Ordinati', digits=(10, 2)),
        'assigned_qty': fields.float('Già assegnati', digits=(10, 2)),
        'available_qty': fields.float('Disponibili', digits=(10, 2)),
        'this_assign_qty': fields.float('Nuova assegnazione', digits=(10, 2)),
        }


class AssignStockToOrderWizardInherit(orm.TransientModel):
    """ Assign stock with order Wizard Relations
    """
    _inherit = 'assign.stock.to.order.wizard'

    _columns = {
        'line_ids': fields.one2many(
            'assign.stock.to.order.line.wizard', 'wizard_id', 'Dettaglio'),
    }


class SaleOrderInherit(orm.Model):
    """ Add extra button
    """
    _inherit = 'sale.order'

    def assign_stock_order_wizard(self, cr, uid, ids, context=None):
        """ Assign stock Wizard
        """
        order_pool = self.pool.get('sale.order')
        wizard_pool = self.pool.get('assign.stock.to.order.wizard')
        line_pool = self.pool.get('assign.stock.to.order.line.wizard')

        model_pool = self.pool.get('ir.model.data')

        order_id = ids[0]
        order = order_pool.browse(cr, uid, order_id, context=context)

        # Wizard lines
        wizard_id = wizard_pool.create(cr, uid, {
            'order_id': order_id,
        }, context=context)

        # Create lines
        for line in order.order_line:
            product = line.product_id
            available_qty = product.mx_lord_mrp_qty

            # todo Check service?

            # Check product availability
            if available_qty <= 0.0:
                _logger.warning('No stock for product {}'.format(
                    product.default_code or product.name,
                ))
                continue

            oc_qty = line.product_uom_qty
            assigned_qty = line.mx_assigned_qty
            this_assign_qty = min(oc_qty, available_qty)
            if this_assign_qty < assigned_qty:
                _logger.warning('Keep always assigned qty if new is less!')
                this_assign_qty = assigned_qty

            line_pool.create(cr, uid, {
                'wizard_id': wizard_id,
                'line_id': line.id,

                'oc_qty': oc_qty,
                'assigned_qty': assigned_qty,
                'available_qty': available_qty,
                'this_assign_qty': this_assign_qty,
            }, context=context)

        # Open Wizard
        form_view = model_pool.get_object_reference(
            cr, uid, 'sale_order_assign_available_stock',
            'assign_stock_to_order_line_wizard_view')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Assegna magazzino',
            'res_model': 'assign.stock.to.order.wizard',
            'res_id': wizard_id,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(form_view, 'form')],
            # 'domain': [('id', 'in', item_ids)],
            'target': 'new',
            'context': context,
        }
