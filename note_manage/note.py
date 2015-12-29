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

class ResNoteTemplate(orm.Model):
    """ Model name: res.note.template
    """
    
    _name = 'res.note.template'
    
    _columns = {
        'propagate': fields.boolean('Propagate',
            help='Propagate down the document'),
        'name': fields.char(
            'Template name', size=64, required=True),     
        'text': fields.text('Text', required=True),
        'note': fields.text('Note'),
        'object': fields.selection([
            # Virtual (to be populated) TODO

            ('sale.order', 'Sale order'),
            ('sale.order.line', 'Sale order line'),

            ('purchase.order', 'Purchase order'),
            ('purchase.order.line', 'Purchase order line'),

            ('stock.picking', 'DDT'),

            ('account.invoice', 'Invoice'),
            ('account.invoice.line', 'Invoice line'),

            ('mrp.production', 'MRP order'),

            ('stock.move', 'Stock move'),
            ], 'Object'), 
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
