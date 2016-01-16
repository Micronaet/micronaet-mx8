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
from openerp import SUPERUSER_ID #. api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class ResPartner(orm.Model):
    ''' Model name: ResPartner
    '''    
    _inherit = 'res.partner'

    def onchange_discount_rates(self, cr, uid, ids, discount_rates, 
            context=None):
        ''' Update value? needed?
        '''    
        # TODO create in necessary this function!!!!!! <<<<<<<<<<<<<<<<<<<<<<<<
        res = self.pool.get('res.partner').format_multi_discount(
             discount_rates)
             
        return {
            'value': {
                'discount_value': res.get('value', 0.0),
                'discount_rates': res.get('text', ''),
                }}    

    # Utility function for compute text and value
    def format_multi_discount(self, multi_discount):
        ''' multi_discount: generic text, like: 50%+30%
            #return {'text': '50.0% + 30.0%', 'value': 65.00}
        '''
        res = {
            'value': 0.0,
            'text': '',
            }
            
        if not multi_discount:
            return res
           
        disc = multi_discount.replace(
            ' ', '').replace(
                ',', '.').replace(
                    '%', '')
        discount_list = disc.split('+')
        if discount_list:
            base_discount = 100.0
            for rate in discount_list:
                try:
                    i = float(eval(rate)) # XXX eval?
                except:
                    i = 0.00
                base_discount -= base_discount * i / 100.0
            res['value'] = 100.0 - base_discount
            res['text'] = ' + '.join(discount_list)
        return res
     
    _columns = {
        'discount_rates': fields.char('Discount scale', size=50),
        # XXX keep value calculation?
        'discount_value': fields.float('Discount value', digits=(16, 2)),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
