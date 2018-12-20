#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
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

class StockPickingGoodsDescription(orm.Model):
    ''' Add extra account reference
    '''
    _inherit = 'stock.picking.goods_description'
    # Aspetto esteriore beni
    
    _columns = {
        'account_ref': fields.char('Account ref', size=2),
        }

class StockPickingTransportationReason(orm.Model):
    ''' Add extra account reference
    '''
    _inherit = 'stock.picking.transportation_reason'
    # Causali di movimento magazzino
    
    _columns = {
        'account_ref': fields.char('Account ref', size=2),
        }

class StockPickingCarriageCondition(orm.Model):
    ''' Add extra account reference
    '''
    _inherit = 'stock.picking.carriage_condition'
    
    _columns = {
        'account_ref': fields.char('Account ref', size=1),
        }

class StockPickingTransportationMethod(orm.Model):
    ''' Add extra account reference
    '''

    _inherit = 'stock.picking.transportation_method'

    _columns = {
        'account_ref': fields.char('Account ref', size=1),
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
