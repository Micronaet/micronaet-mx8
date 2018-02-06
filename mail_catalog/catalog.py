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

class ResPartnerDocLeaved(orm.Model):
    """ Model name: ResPartnerDocLeaved
    """    
    _name = 'res.partner.doc.leaved'
    _description = 'Document leaved'
    _rec_name = 'date'
    _order = 'date desc'
    
    _columns = {
        'partner_id': fields.many2one(
            'res.partner', 'Partner', 
            required=False),
        'date': fields.date('Date', required=True),    
        'note': fields.char('Note', size=180),
        'mode': fields.selection([
            ('catalog', 'Catalog'),
            ('banner', 'Banner'),
            ], 'mode'),
        }
        
    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        'mode': lambda *x: 'catalog',
        }

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'mail_catalog': fields.boolean('Catalog'),
        'mail_catalog_note': fields.text('Catalog note'),
        'mail_banner': fields.boolean('Banner'),
        'mail_banner_note': fields.text('Banner note'),
        'catalog_ids': fields.one2many(
            'res.partner.doc.leaved', 'partner_id', 'Catalog leaved'),
        #'banner_ids': fields.one2many(
        #    'res.partner.doc.leaved', 'partner_id', 'Catalog leaved'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
