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

class CreateSaleOrderDeliveryWizard(orm.TransientModel):
    ''' Create delivery order from sale order
    '''    
    _name = 'create.sale.order.delivery.wizard'
    
    # --------------
    # Wizard button:
    # --------------
    def action_create_delivery_order(self, cr, uid, ids, context=None):
        ''' Create delivery order from sale
        '''
        if context is None:
           context = {}

        # Wizard proxy:
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Pool used:
        delivery_pool = self.pool.get('sale.order.delivery')
        sale_pool = self.pool.get('sale.order')
        
        sale_ids = context.get('active_ids', False)
        partner_id = False
        for sale in sale_pool.browse(cr, uid, sale_ids, context=context):
            if not partner_id:
                partner_id = sale.partner_id.id
            if partner_id != sale.partner_id.id:
                raise osv.except_osv(
                    _('Error'),
                    _('Delivery order must have order with same partner'
                    ))
        
        delivery_id = delivery_pool.create(cr, uid, {
            'partner_id': partner_id,
            'note': wiz_proxy.note,
            }, context=context)
        
        # Assign order to delivery:
        sale_pool.write(cr, uid, sale_ids, {
            'multi_delivery_id': delivery_id}, context=context)

        return {
            'view_type': 'form',
            'view_mode': 'form',#,tree',
            'res_model': 'sale.order.delivery',
            #'views': views,
            #'domain': [('id', '=', delivery_id)], 
            #'views': [(view_id, 'form')],
            #'view_id': delivery_id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': delivery_id,
            }
            

    # -----------------
    # Default function:        
    # -----------------
    def default_error(self, cr, uid, context=None):
        ''' Check that order has all same partner
        '''
        sale_pool = self.pool.get('sale.order')
        sale_ids = context.get('active_ids', False)
        partner_id = False
        for sale in sale_pool.browse(cr, uid, sale_ids, context=context):
            if not partner_id:
                partner_id = sale.partner_id.id
            if partner_id != sale.partner_id.id:
                return 'Delivery order must have order with same partner'                
                #raise osv.except_osv(
                #    _('Error'),
                #    _('Delivery order must have order with same partner'
                #    ))
        return False        
                    
        
    def default_oc_list(self, cr, uid, context=None):
        ''' Show in html order list
        '''        
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
        res += "</table>" # close table for list element
        return res
   
    _columns = {
        'note': fields.text('Note'),
        'error': fields.text('Error', readonly=True),
        'order_list': fields.text('Order list', readonly=True),
        }
        
    _defaults = {
        'error': lambda s, cr, uid, c: s.default_error(
            cr, uid, context=c),
        'order_list': lambda s, cr, uid, c: s.default_oc_list(
            cr, uid, context=c),
         }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
