# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    Original module for stock.move from:
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class StockPicking(orm.Model):
    ''' Add button event:
    '''
    _inherit = 'stock.picking'
    
    # Button event:
    def open_pick_out(self, cr, uid, ids, context=None):
        ''' Open document Pick
        '''
        return {}

    def open_ddt(self, cr, uid, ids, context=None):
        ''' Open document DDT
        '''
        return {}

    def open_order(self, cr, uid, ids, context=None):
        ''' Open document DDT
        '''
        return {}
        
        
class AccountInvoice(orm.Model):
    ''' Add some extra field used in report and in management as account
        invoice
    '''
    _inherit = 'account.invoice'
    
    def link_pickout_document(self, cr, uid, ids, context=None):
        ''' Link pick out depend on origin text
        '''
        assert len(ids), 'Run only with one record!'
        
        pick_pool = self.pool.get('stock.picking')
        origin = self.browse(cr, uid, ids, context=context)[0].origin
        if origin:
            origins = origin.split(', ')
            # not linked:
            pick_ids = pick_pool.search(cr, uid, [
                ('name', 'in', origins),
                ('invoice_id', '=', False),
                ], context=context)
            if pick_ids:
                pick_pool.write(cr, uid, pick_ids, {
                    'invoice_id': ids[0],
                    }, context=context)
                _logger.warning('Linked pick to invoice: %s' % origin)
        return True             

    # Override partner_id onchange for set up carrier_id
    def onchange_partner_id(self, cr, uid, ids, type, partner_id, date_invoice, 
            payment_term, partner_bank_id, company_id, context=None):
        ''' Set also carrier ID and default payment
        '''    
        res = super(AccountInvoice, self).onchange_partner_id(
            cr, uid, ids, type, partner_id, date_invoice, 
            payment_term, partner_bank_id, company_id, context=context)
        
        if partner_id:
            partner_pool = self.pool.get('res.partner')
            partner_proxy = partner_pool.browse(
                cr, uid, partner_id, context=context)
            res['value'][
                'default_carrier_id'] = partner_proxy.default_carrier_id.id
            if len(partner_proxy.bank_ids) == 1:
                res['value'][
                    'used_bank_id'] = partner_proxy.bank_ids[0].id
        else:
            res['value']['default_carrier_id'] = False
            res['value']['used_bank_id'] = False
        return res    

    # ------------------------------------
    # Override validation for update pick:   
    # ------------------------------------
    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(AccountInvoice, self).invoice_validate(cr, uid, ids, 
            context=context)
            
        # Unload pick stock:
        _logger.info('Update pick out moves')    
        move_pool = self.pool.get('stock.move')
        pick_pool = self.pool.get('stock.picking')
        
        # ---------------------------------------
        # Update pick and assign to this invoice:
        # ---------------------------------------
        # Run launching button:
        self.link_pickout_document(cr, uid, ids, context=context)

        # -------------------------------------
        # Set confirmed transfer when validate:
        # -------------------------------------
        pick_ids = pick_pool.search(cr, uid, [
            ('invoice_id', 'in', ids),
            ], context=context)
        
        todo = []
        for pick in pick_pool.browse(cr, uid, pick_ids,
                context=context):
            # confirm all picking
            for move in pick.move_lines:
                if move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
        if todo:
            move_pool.action_done(cr, uid, todo, context=context)
            _logger.info('>>>>>> Pick out moves: %s' % (todo, ))    
        return res
        
    _columns = {
        'direct_invoice': fields.boolean('Direct invoice'), # TODO use it!
        'start_transport': fields.datetime('Start transport', 
            help='Used in direct invoice'),
        'used_bank_id': fields.many2one('res.partner.bank', 'Used bank',
            help='Partner bank account used for payment'),
        'default_carrier_id': fields.many2one(
            'delivery.carrier', 'Carrier'), 
        'invoice_type': fields.selection([
            ('ft1', 'FT 1 (normal)'),
            ('ft2', 'FT 2 ()'),
            ('ft3', 'FT 3 ()'),
            ], 'Invoice module'),

        'invoiced_picking_ids': fields.one2many(
            'stock.picking', 'invoice_id', 'Picking'), 
        }    
        
    _defaults = {
        'invoice_type': lambda *x: 'ft1',
        }    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
