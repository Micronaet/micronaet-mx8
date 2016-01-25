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


class ResCompany(orm.Model):
    """ Model name: ResCompany
    """    
    _inherit = 'res.company'
    
    _columns = {
        'stock_report_unload_ids': fields.many2many(
            'stock.picking.type', 'company_picking_out_rel', 
            'company_id', 'type_id', 
            'Pick out type'), 
        'stock_report_load_ids': fields.many2many(
            'stock.picking.type', 'company_picking_in_rel', 
            'company_id', 'type_id', 
            'Pick in type'),

        'stock_explude_partner_ids': fields.many2many(
            'res.partner', 'company_picking_exclude_partner_rel', 
            'company_id', 'partner_id', 
            'Exclude partner', 
            help='Other company partner ID'), 
        
        'is_remote_stock': fields.boolean('Is remote company', 
            help='If is remote company no XMLRPC connection'),
        'remote_name': fields.char('XMLRPC DB name', size=80),
        'remote_hostname': fields.char('XMLRPC Hostname', size=80),
        'remote_port': fields.integer('XMLRPC Port'),
        'remote_username': fields.char('XMLRPC Username', size=80),
        'remote_password': fields.char('XMLRPC Password', size=80),
        }

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'

    def print_stock_status_report(self, cr, uid, ids, context=None):
        ''' Print report product stock
        '''
        if context is None: 
            context = {}            
                    
        datas = {}
        datas['partner_id'] = ids[0]
        datas['partner_name'] = self.browse(
            cr, uid, ids, context=context)[0].name
                       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock_status_multicompany_report',
            'datas': datas,
            }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
