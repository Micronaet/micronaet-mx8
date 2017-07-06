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
from calendar import monthrange
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

class StatisticDeadline(orm.Model):
    """ Model name: StatisticDeadline
    """
    
    _inherit = 'statistic.deadline'

    def _get_fido_deadline_date(
            self, cr, uid, ids, fields, args, context=None):
        ''' Add period to end month from date
        '''
        # XXX Static parameter (put in ODOO?)
        months = 6
        end_month = True    

        res = {}
        for line in self.browse(cr, uid, ids, context=None):
            # Check if there's FIDO:
            if line.partner_id.fido_total <= 0:
                res[line.id] = False
                continue
                
            date = datetime.strptime(
                line.invoice_date, DEFAULT_SERVER_DATE_FORMAT)
            fido_deadline = date + relativedelta(months=months)
            month_range = monthrange(
                fido_deadline.year, fido_deadline.month)
            if end_month:
                res[line.id] = '%s-%s' % ( 
                    fido_deadline.strftime('%Y-%m'),
                    month_range[1],
                    )
            else:        
                res[line.id] = fido_deadline.strftime('%Y-%m-%d')                
        return res    
    
    _columns = {
        'fido_total': fields.related(
            'partner_id', 'fido_total', type='float', string='FIDO Total'),
        'agent_id': fields.related(
            'partner_id', 'agent_id', 
            type='many2one', relation='res.partner', string='Agent'),    
        'fido_deadline': fields.function(
            _get_fido_deadline_date, method=True, type='date', 
            string='FIDO deadline', store=True), 
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
