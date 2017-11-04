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

class EmailTemplace(orm.Model):
    """ Model name: Email Template
    """
    
    _inherit = 'email.template'
    
    _columns = {
        'default_send': fields.boolean('Default send', 
            help='This is the default proposed in mail wizard'),
        }

class AccountInvoice(orm.Model):
    """ Model name: AccountInvoice
    """
    
    _inherit = 'account.invoice'
    
    def action_invoice_sent(self, cr, uid, ids, context=None):
        ''' Override and change default
        '''
        res = super(AccountInvoice, self).action_invoice_sent(
            cr, uid, ids, context=context)
        template_pool = self.pool.get('email.template')
        template_ids = template_pool.search(cr, uid, [
            ('default_send', '=', True),
            ('model', '=', 'account.invoice'),
            ], context=context)
        if not template_ids: # no default use previous
            return res 
        res['context'].update({
            'default_use_template': True,
            'default_template_id': template_ids[0],            
            })
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
