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
import pytz
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class SaleOrder(orm.Model):
    ''' Add alternative method for picking creation
    '''
    _inherit = 'sale.order'

    # Copy here from v. 7.0
    def date_to_datetime(self, cr, uid, userdate, context=None):
        """ Convert date values expressed in user's timezone to
        server-side UTC timestamp, assuming a default arbitrary
        time of 12:00 AM - because a time is needed.
    
        :param str userdate: date string in in user time zone
        :return: UTC datetime string for server-side use
        """
        # TODO: move to fields.datetime in server after 7.0
        user_date = datetime.strptime(
            userdate[:10], 
            DEFAULT_SERVER_DATE_FORMAT)
        if context and context.get('tz'):
            tz_name = context['tz']
        else:
            tz_name = self.pool.get('res.users').read(
                cr, SUPERUSER_ID, uid, ['tz'])['tz']
        if tz_name:
            utc = pytz.timezone('UTC')
            context_tz = pytz.timezone(tz_name)
            user_datetime = user_date + relativedelta(hours=12.0)
            local_timestamp = context_tz.localize(user_datetime, is_dst=False)
            user_datetime = local_timestamp.astimezone(utc)
            return user_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return user_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    # Override method from sale_stock module to keep here!
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, 
            date_planned, context=None):
        ''' Create a record dict of stock.move
        '''    
        # TODO no more shop_id!!!
        type_pool = self.pool.get('stock.picking.type')
        type_ids = type_pool.search(cr, uid, [
            ('code', '=', 'outgoing')], context=context)
        if not type_ids:
            _logger.error('Type outgoing not found')
            # TODO raise error!
            return {}
            
        type_proxy = type_pool.browse(cr, uid, type_ids, context=context)[0]    
        location_id = type_proxy.default_location_src_id.id
        output_id = type_proxy.default_location_dest_id.id

        #location_id = order.shop_id.warehouse_id.lot_stock_id.id
        #output_id = order.shop_id.warehouse_id.lot_output_id.id
        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or\
                line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or \
                order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            #'tracking_id': False,
            'state': 'draft',
            #'state': 'waiting',
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0
            }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        ''' Create a record dict of stock.picking order
        '''
        context = context or {}
        
        type_pool = self.pool.get('stock.picking.type')
        type_ids = type_pool.search(cr, uid, [
            ('code', '=', 'outgoing')], context=context)
        if not type_ids:
            _logger.error('Type outgoing not found')
            # TODO raise error!
            return {}
                
        # Create on date deadline if present:
        date = context.get(
            'force_date_deadline', 
            self.date_to_datetime(cr, uid, order.date_order, context))
        pick_name = self.pool.get('ir.sequence').get(
            cr, uid, 'stock.picking.out')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': date,
            #'type': 'out',
            'picking_type_id': type_ids[0],
            'state': 'done', # TODO removed: 'auto',
            'move_type': order.picking_policy,

            # TODO create using group_id instead of sale_id
            'group_id': order.procurement_group_id.id,
            'sale_id': order.id, # TODO no more used!
            
            # Partner in cascade assignment:
            'partner_id': order.partner_id.id or \
                order.address_id.id or order.partner_shipping_id.id,
            'note': order.note,
            'invoice_state': (
                order.order_policy=='picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
            }


    # -------------------------------------------------------------------------
    #                      Alternative method (not overrided)
    # -------------------------------------------------------------------------    
    def _create_pickings_from_wizard(self, cr, uid, order, order_line_ids, 
            context=None):            
        """ Alternative method of _create_pickings_and_procurements
            order: browse obj as order source
            order_line: dict of order line and qty to pick out
        """
        context = context or {}
        
        # Pool used:        
        line_pool = self.pool.get('sale.order.line')
        move_pool = self.pool.get('stock.move')
        picking_pool = self.pool.get('stock.picking')

        # Browse obj used:
        order_line = line_pool.browse(cr, uid, order_line_ids.keys(), 
            context=context)
        
        # ---------------------------------------------------------------------
        # Picking creation:
        # ---------------------------------------------------------------------
        # Get normal data from original function:
        picking_data = self._prepare_order_picking(
            cr, uid, order, context=context)

        # Add extra fields to picking:
        picking_data['date'] = context.get(
            'force_date_deadline', False) or datetime.now().strftime(
                DEFAULT_SERVER_DATE_FORMAT)
        
        # Add dependency for this fields: TODO vector and others needed!
        extra_fields_m2o = (
            # DDT ref:
            'mx_agent_id',
            'transportation_reason_id', 
            'goods_description_id', 'carriage_condition_id',
            # Partner ref.:
            'destination_partner_id', 'invoice_partner_id',)
        extra_fields = (
            # Header note ref.:
            'text_note_pre', 'text_note_post')

        for field in extra_fields_m2o:
            picking_data[field] = order.__getattribute__(field).id
        for field in extra_fields:
            picking_data[field] = order.__getattribute__(field)
        
        # TODO Keep picking invoiceable???
        #picking_data['invoice_state'] = '2binvoiced'
        
        # Create record    
        picking_id = picking_pool.create(cr, uid, picking_data, 
            context=context)
        
        # ---------------------------------------------------------------------
        #                    TODO Split depend on deadline date
        # ---------------------------------------------------------------------
        # TODO update virtual availability after create picking
        for line in order_line:
            #if line.state == 'done':
            #    continue
            if line.product_id:
                if line.product_id.type in ('product', 'consu'): # not service
                    move_data = self._prepare_order_line_move(
                        cr, uid, order, line, picking_id, 
                        picking_data['date'],
                        context=context)

                    # Force qty:
                    #product_uom_qty = order_line_ids[line.id]                        
                    move_data['product_uos_qty'] = order_line_ids[line.id]                        
                    move_data['product_uom_qty'] = order_line_ids[line.id]                        
                    
                    # TODO workflow brutal forced: ****************************
                    move_data['state'] = 'assigned' # TODO controllare se è corretto!!!!
                    # *********************************************************
                    move_data['invoice_state'] = '2binvoiced'
                    
                    # OC Field to move on:
                    move_data[
                        'use_text_description'] = line.use_text_description
                    move_data['text_note_pre'] = line.text_note_pre
                    move_data['text_note_post'] = line.text_note_post                        
                    
                    if not move_data['product_uom_qty']:
                        continue
                    move_id = move_pool.create(
                        cr, uid, move_data, context=context)
                else:
                    # a service has no stock move
                    move_id = False

        wf_service = netsvc.LocalService('workflow') # TODO deprecated!
        if picking_id:
            wf_service.trg_validate(
                uid, 'stock.picking', picking_id, 'button_confirm', cr)
        return picking_id
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
