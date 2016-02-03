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
    """ Model name: SaleOrder
    """
    
    _inherit = 'sale.order'

    # BUtton event:    
    def update_parcels_event(self, cr, uid, ids, context=None):
        ''' Get total of parcels
        '''
        assert len(ids) == 1, 'Only one element a time'
        
        parcels = 0
        parcels_note:
        for line in self.browse(cr, uid, ids, context=context)[0].order_line:
            qty = line.product_uom_qty 
            q_x_pack = line.product_id.q_x_pack
            if q_x_pack > 0:
                if qty % q_x_pack > 0:
                    parcels_note += _('%s not correct q x pack\n') % (
                        line.product_id.default_code)
                else:
                    parcel = int(qty / q_x_pack)
                    line.product_uom_qty += parcel 
                    parcels_note += _('%s: parcels %s \n') % (
                        line.product_id.default_code, parcel)
            else:
                parcels_note += _(
                    '%s no q x pack\n') % line.product_id.default_code    

        self.write(cr, uid, ids, {
            'parcels': parcels,
            'parcels_note': parcels_note,
            }, context=context)            
                
    _columns = {
        'parcels_note': fields.text(
            'Parcel note', help='Calculation procedure note') ,
        }            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
