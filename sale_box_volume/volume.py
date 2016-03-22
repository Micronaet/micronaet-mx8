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

class StockDdtVolume(orm.Model):
    """ Model name: StockDdtVolume
    """    
    _name = 'stock.ddt.volume'
    _description = 'Volume box'
    _rec_name = 'dimension_l'
    
    _columns = {
        'dimension_l': fields.float('L (cm.)', digits=(16, 2)),
        'dimension_h': fields.float('H (cm.)', digits=(16, 2)),
        'dimension_s': fields.float('S (cm.)', digits=(16, 2)),        
        'ddt_id': fields.many2one('stock.ddt', 'DDT'),
        }

class StockDdt(orm.Model):
    """ Model name: StockDdt
    """    
    _inherit = 'stock.ddt'
    
    def compute_volume_total(self, cr, uid, ids, context=None):
        ''' Compute volume total
        '''
        assert len(ids) == 1, 'Once a time!'
        ddt_proxy = self.browse(cr, uid, ids, context=context)[0]
        total = 0.0
        for pack in ddt_proxy.volume_ids:
            total += pack.dimension_l * pack.dimension_h * pack.dimension_s
            
        return self.write(cr, uid, ids, {
            'volume_total': total / 1000000.0}, context=context)
        
    _columns = {
        'volume_ids': fields.one2many(
            'stock.ddt.volume', 'ddt_id', 'Volume (m3)'), 
        'volume_total': fields.float('Tot. volume', digits=(16, 2)),     
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
