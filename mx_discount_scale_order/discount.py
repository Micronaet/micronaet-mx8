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


class SaleOrder(orm.Model):
    ''' Model name: SaleOrder
    '''    
    _inherit = 'sale.order'
    
    _columns = {
        'multi_discount_rates': fields.char('Discount scale', size=30, 
            help='Use for force the one in lines'),
        }

class SaleOrderLine(orm.Model):
    ''' Model name: SaleOrderLine
    '''
    _inherit = 'sale.order.line'

    def create(self, cr, uid, vals, context=None):
        ''' Correct multi discount description and calculare if discount
            not present
        '''
        multi_discount_rates = vals.get('multi_discount_rates', False)
        if not vals.get('discount', 0.0) and multi_discount_rates):
            res = self.pool.get(
                'res.partner').format_multi_discount(multi_discount_rates)

            vals['discount'] = res.get('value', 0.0)
            vals['multi_discount_rates'] = res.get('text', 0.0)
            
        return super(SaleOrderLine, self).create(
            cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        ''' Update discount if text is present
        '''

        if vals.get('multi_discount_rates', False):
            res = self.pool.get(
                'res.partner').format_multi_discount(
                    multi_discount_rates)
                
            vals['discount'] = res.get('value', 0.0)
            vals['multi_discount_rates'] = res.get('text', 0.0)
        return super(SaleOrderLine, self).write(
            cr, uid, ids, vals, context=context)

    def _discount_rates_get(self, cr, uid, attribute, context=None):
        if context is None:
            context = {}
        partner_pool = self.pool.get('res.partner')    
        partner_id = context.get('partner_id')
        if not partner_id:
            return False
        
        partner_proxy = partner_pool.browse(
            cr, uid, partner_id, context=context)

        return partner_proxy.__getattribute__(attribute)        

    def on_change_multi_discount(self, cr, uid, ids, multi_discount_rates, 
            context=None):
        ''' Change multi_discount_rates and value
        '''
        res = self.pool.get('res.partner').format_multi_discount(
             multi_discount_rates)
             
        return {
            'value': {
                'discount': res.get('value', 0.0),
                #'multi_discount_rates': res.get('text', ''),
                }}    
    
    _columns = {
        'multi_discount_rates': fields.char('Discount scale', size=30),
        
        # TODO Used:?
        'price_use_manual': fields.boolean('Use manual net price',
            help='If specificed use manual net price instead of '
                'lord price - discount'),
        'price_unit_manual': fields.float(
            'Manual net price', digits_compute=dp.get_precision('Sale Price')),
        }

    _defaults = {
        'multi_discount_rates': lambda s, cr, uid, ctx: s._discount_rates_get(
            cr, uid, 'discount_rates', context=ctx),
        'discount':  lambda s, cr, uid, ctx: s._discount_rates_get(
            cr, uid, 'discount_value', context=ctx),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
