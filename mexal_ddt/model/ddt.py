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
#from openerp import models
from openerp.osv import fields, osv, expression, orm#, models
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

class StockDdt(orm.Model):
    _inherit = 'stock.ddt'

    def open_ddt_report(self, cr, uid, ids, context=None):
        ''' Open DDT form if present        
        '''
        assert len(ids) == 1, 'Only one picking!'

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'custom_ddt_report',
            'datas': context,
            }         

    # Override for confirm all picking    
    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirmed'})

        move_pool = self.pool.get('stock.move')
        todo = []
        for pick in self.picking_ids:
            # confirm all picking
            for move in pick.move_lines:
                if move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
        if todo:
            move_pool.action_done(self.env.cr, self.env.uid, todo, 
                context=self.env.context)
                        
        #TODO if start from draft...
        #for pick in self.browse(cr, uid, ids, context=context):
        #    for move in pick.move_lines:
        #        if move.state == 'draft':
        #            todo.extend(self.pool.get('stock.move').action_confirm(
        #                cr, uid, [move.id], context=context))

    _columns = {
        'used_bank_id': fields.many2one('res.partner.bank', 'Used bank',
            help='Partner bank account used for payment'),

        'payment_term_id': fields.many2one(
            'account.payment.term', 'Payment term'),

        # XXX there's also carrier_id...
        'default_carrier_id': fields.many2one(
            'delivery.carrier', 'Default carrier'),     
        }

class StockPicking(orm.Model):
    # TODO remove!!!
    _inherit = 'stock.picking'
    
    _columns = {
        'used_bank_id': fields.many2one('res.partner.bank', 'Used bank',
            help='Partner bank account used for payment'),        
        }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
