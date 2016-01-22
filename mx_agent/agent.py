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
    """ Model name: Sale Order
    """    
    _inherit = 'sale.order'
    
    # TODO onchange for setup from partner
    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = super(SaleOrder, self).on_change_partner_id(
            cr, uid, ids, partner_id, context=context)
            
        
        # Update agent field for partner form
        # TODO propagate!!!
        if 'value' not in res:
           res['value'] = {}
        if partner_id:
           partner_proxy = self.pool.get('res.partner').browse(
               cr, uid, partner_id, context=context)
           res['value'][
               'mx_agent_id'] = partner_proxy.agent_id.id
        else:       
               
           res['value']['mx_agent_id'] = False
        return res 
    
    
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }

class AccountInvoice(orm.Model):
    """ Model name: Account Invoice
    """    
    _inherit = 'account.invoice'
    
    # TODO onchange for setup from partner
    
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }

class StockPicking(orm.Model):
    """ Model name: Stock Picking    
    """    
    _inherit = 'stock.picking'
    
    # TODO onchange for setup from partner
    
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }

class StockDdt(orm.Model):
    """ Model name: Stock DDT
    """    
    _inherit = 'stock.ddt'
    
    # TODO onchange for setup from partner
   
    _columns = {
        'mx_agent_id': fields.many2one('res.partner', 'Agent', 
            domain=[('is_agent', '=', True)]),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
