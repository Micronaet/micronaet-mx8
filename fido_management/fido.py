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

# TODO move in a module:
# TODO REMOVE !!!!
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
class SaleOrder(orm.Model):
    ''' FIDO in order 
    '''
    _inherit ='sale.order'
    
    def _get_open_amount_total_order(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = 0.0
            for line in order.order_line:
                remain = line.product_uom_qty - line.delivered_qty
                if remain and line.product_uom_qty:
                    res[order.id] += \
                        line.price_subtotal * remain / line.product_uom_qty
        return res

    _columns = {
        'open_amount_total': fields.function(
            _get_open_amount_total_order, method=True, 
            type='float', string='Open amount', 
            store=False),                         
        }
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# -----------------------------------------------------------------------------
# NO FIDO Management:
# -----------------------------------------------------------------------------
class ResUsers(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'res.users'
   
    def set_no_inventory_status(self, cr, uid, value=False, context=None):
        ''' Set inventory status uid
            return previous value
            default is True
        '''
        user_proxy = self.browse(cr, uid, uid, context=context)
        
        previous = user_proxy.no_inventory_status
        self.write(cr, uid, uid, {
            'no_fido_status': value
            }, context=context)
        _logger.warning('>>> Set user [%s] No FIDO status: %s > %s' % (
            user_proxy.login, previous, value))
        return previous
            
    _columns = {
        'no_fido_status': fields.boolean('No FIDO status'),
        }

# TODO move away:
class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order'
   
    def set_context_no_fido(self, cr, uid, ids, context=None):
        ''' Set no inventory in res.users parameter
        '''
        _logger.info('Stop fido for user: %s' % uid)
        self.pool.get('res.users').write(cr, uid, [uid], {
            'no_fido_status': True,
            }, context=context)
        return     

    def set_context_yes_fido(self, cr, uid, ids, context=None):
        ''' Set no inventory in res.users parameter
        '''    
        _logger.info('Start fido for user: %s' % uid)
        self.pool.get('res.users').write(cr, uid, [uid], {
            'no_fido_status': False,
            }, context=context)
        return            
# -----------------------------------------------------------------------------

class StockPicking(orm.Model):
    ''' FIDO in ddt 
    '''
    _inherit ='stock.picking'
    
    def _get_open_amount_total_ddt(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for ddt in self.browse(cr, uid, ids, context=context):
            res[ddt.id] = 0.0
            for line in ddt.move_lines:
                qty = line.product_uom_qty
                
                if qty:
                    # Proportional with subtotal referred in order line:
                    if line.sale_line_id.product_uom_qty:
                        res[ddt.id] += \
                            line.sale_line_id.price_subtotal * qty / \
                                line.sale_line_id.product_uom_qty
                    else:
                        _logger.info('Division by zero!!')            
        return res
        
    _columns = {
        'open_amount_total': fields.function(
            _get_open_amount_total_ddt, method=True, 
            type='float', string='Open amount', 
            store=False),                         
        }

class ResPartner(orm.Model):
    ''' FIDO fields for add management
    '''
    _inherit ='res.partner'
    
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def res_partner_return_form_view(self, cr, uid, ids, context=None):
        ''' Open form partner
        '''
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, uid, 'base','view_partner_form')[1]
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('FIDO Detail'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': ids[0],
            'res_model': 'res.partner',
            'view_id': view_id, # False
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    def res_partner_fido_detail(self, cr, uid, ids, context=None):
        ''' Open form FIDO detail
        '''
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, 
            uid, 
            'fido_management', 
            'view_res_partner_fido_details_form',
            )[1]
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('FIDO Detail'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': ids[0],
            'res_model': 'res.partner',
            'view_id': view_id, # False
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    def _get_uncovered_amount_total(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        fido_yellow = 0.85 # TODO parametrize?
        
        # ---------------------------------------------------------------------
        # Read parameter for FIDO:
        # ---------------------------------------------------------------------
        _logger.warning('START FIDO CHECK')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        no_fido_status = user.no_fido_status
        if no_fido_status:
            _logger.error('USER: %s NO FIDO INFORMATION' % uid)
        else:
            _logger.info('USER: %s FIDO INFORMATION' % uid)
        
        for partner in self.browse(cr, uid, ids, context=context):       
            if no_fido_status:
                res[partner.id] = {
                    'uncovered_amount': 0, 
                    'uncovered_state': 'grey',
                    }
                continue 

            res[partner.id] = {}
            opened = 0.0 # total
            fido_date = partner.fido_date or False
            fido_total = partner.fido_total or 0.0

            # ---------------------------
            # Payment in date not closed:
            # ---------------------------
            for payment in partner.open_payment_ids:
                invoice_date = payment.invoice_date or payment.deadline or False
                if not fido_date or not invoice_date or \
                        fido_date <= invoice_date:
                    opened += payment.__getattribute__('in')
            
            # ----------
            # OC opened:
            # ----------
            for order in partner.open_order_ids:
                opened += order.open_amount_total
                
            # ----------------
            # DDT not invoice:
            # ----------------
            for ddt in partner.open_picking_ids:
                opened += ddt.open_amount_total  

            res[partner.id]['uncovered_amount'] = fido_total - opened

            # Check black listed:
            if partner.fido_ko: # No computation partner is black listed!
                res[partner.id]['uncovered_state'] = 'black'
            elif not fido_total or fido_total < opened: # No Fido amount!
                res[partner.id]['uncovered_state'] = 'red'
            elif opened / fido_total > fido_yellow:
                res[partner.id]['uncovered_state'] = 'yellow'
            else:    
                res[partner.id]['uncovered_state'] = 'green'                
        _logger.warning('END FIDO CHECK')
        return res
        
    _columns = {
        'empty': fields.char(' '),
        'fido_date': fields.date('FIDO from date'),
        'fido_ko': fields.boolean('FIDO removed'),
        'fido_total': fields.float('Total FIDO', digits=(16, 2)),
        
        # Open order:
        'open_order_ids': fields.one2many(
            'sale.order', 'partner_id', 
            'Order open', domain=[
                ('mx_closed', '=', False),
                ('pricelist_order', '=', False),
                ('state', 'not in', ('cancel', 'draft', 'sent')),
                ]), 
            
        # Open order:
        'open_picking_ids': fields.one2many(
            'stock.picking', 'partner_id', 
            'Open DDT', domain=[
                ('ddt_id', '!=', False), 
                ('invoice_id', '=', False),
                ]),

        'uncovered_amount': fields.function(
            _get_uncovered_amount_total, method=True, 
            type='float', string='Uncovered amount', 
            store=False, multi=True),
        'uncovered_state': fields.function(
            _get_uncovered_amount_total, method=True, 
            type='selection', string='Uncovered state', 
            store=False, multi=True, selection=[
                ('green', 'OK FIDO'),
                ('yellow', '> 85% FIDO'),
                ('red', 'FIDO uncovered or no FIDO'),
                ('black', 'FIDO removed'),
                ('grey', 'No FIDO check'),                
                ]),
        }
        
    _defaults = {
        'empty': lambda *x: ' ',
        }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
