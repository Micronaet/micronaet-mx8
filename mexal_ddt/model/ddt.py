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
    _inherit = 'stock.picking'
    
    _columns = {
        'used_bank_id': fields.many2one('res.partner.bank', 'Used bank',
            help='Partner bank account used for payment'),        
        }
    # -------------    
    # Button event:    
    # ------------- 
    def print_ddt(self, cr, uid, ids, context=None):
        ''' Print report (for pop up form)
        '''   
        return { # action report
            'type': 'ir.actions.report.xml',
            'report_name': 'custom_ddt_report',
            'datas': context,
            }            
        
    def force_assign_ddt(self, cr, uid, ids, context=None):
        ''' Force assign of DDT after change state
        '''
        assert len(ids), 'Must me only one record!'
        if context is None:
            context = {}
            
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot process picking without stock moves.'))
           
            # Changhe state without workflow:
            # > Line:
            line_ids = [item.id for item in pick.move_lines]
            self.pool.get('stock.move').write(cr, uid, line_ids, {
                'state': 'done'}, context=context)

        # > Pickout:    
        self.write(cr, uid, ids, {
            'state': 'done'}, context=context)

        # Assign DDT (call directly ex. Wizard button):
        ctx = context.copy()
        ctx['active_ids'] = ids # needed list
        
        # TODO set current date for delivery ?? 
        # TODO correct!!?!?!
        return self.pool.get('wizard.assign.ddt').assign_ddt(
            cr, uid, ids, context=ctx)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
