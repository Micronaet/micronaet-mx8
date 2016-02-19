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
    ''' FIDO in order 
    '''
    _inherit = 'sale.order'
    
    def _get_fido_detailed_info(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        assert len(ids)==1, 'Only one by one'
        res = {}
        partner_proxy = self.browse(
            cr, uid, ids, context=context)[0].partner_id
        res[ids[0]] = _('FIDO: %s\nDate: %s\nState: %s\nUncovered: %s\n%s') % (
            ("{:,}".format(int(
                partner_proxy.fido_total or 0))).replace(',','.') ,
            partner_proxy.fido_date or '',
            partner_proxy.uncovered_state or '',
            ("{:,}".format(int(
                partner_proxy.uncovered_amount or 0))).replace(',','.') ,            
            _('REMOVED!!!') if partner_proxy.fido_ko else ''
            )
        return res    
        
    def _get_uncovered_amount_total(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            if not order.partner_id:
               res[order.id] = False
            else:   
                res[order.id] = order.partner_id.uncovered_state
        return res        

    _columns = {
        'fido_detailed_info': fields.function(
            _get_fido_detailed_info, method=True, 
            type='text', string='FIDO info', 
            store=False), 
                        
        'empty': fields.char(' '),
        'uncovered_state': fields.function(
            _get_uncovered_amount_total, method=True, 
            type='selection', string='Uncovered state', 
            store=False, selection=[
                ('green', 'OK FIDO'),
                ('yellow', '> 85% FIDO'),
                ('red', 'FIDO uncovered or no FIDO'),
                ('black', 'FIDO removed'),
                ]),
        }

    _defaults = {
        'empty': lambda *x: ' ',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
