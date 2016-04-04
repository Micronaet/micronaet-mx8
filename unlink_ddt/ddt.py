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

class StockDdt(orm.Model):
    """ Model name: StockDdt
    """    
    _inherit = 'stock.ddt'
    
    # Button event:
    def unlink_ddt_elements(self, cr, uid, ids, context=None):
        ''' Remove DDT and restore all elements            
        '''
        assert len(ids) == 1, 'Only one DDT a time!'
        
        # Pool used:
        move_pool = self.pool.get('stock.move')
        picking_pool = self.pool.get('stock.picking')
        
        # ---------------------------------------------------------------------
        #                             Remove picking
        # ---------------------------------------------------------------------
        ddt_proxy = self.browse(cr, uid, ids, context=context)[0]
        for picking in ddt_proxy.picking_ids:
            # -------------------------------
            # Remove stock move lines before:
            # -------------------------------
            move_ids = [move.id for move in picking.move_lines]            
            # Set to draft:
            move_pool.write(cr, uid, move_ids, {
                'state': 'draft'}, context=context)            
            # Delete:
            move_pool.unlink(cr, uid, move_ids, context=context)                
            _logger.warning('Remove move: %s' % (move_ids, ))
                
            # ------------------------
            # TODO Log event in order:
            # ------------------------
            order_id = False # TODO
            
            # ---------------
            # Remove picking:
            # ---------------
            picking_pool.unlink(cr, uid, [picking.id], context=context)
            _logger.warning('Remove picking: %s' % picking.name)

        # ---------------------------------------------------------------------
        #                           Remove DDT element:
        # ---------------------------------------------------------------------
        self.unlink(cr, uid, ids, context=context)        
        _logger.warning('Remove DDT: %s' % ddt_proxy.name)
        # TODO restore counter for get same number (user operation!)
        return True
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
