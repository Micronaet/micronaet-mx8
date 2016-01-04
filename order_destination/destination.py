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

class ResPartner(orm.Model):
    ''' Change name_get for show address
    ''' 
    _inherit = 'res.partner'
    
    def name_get(self, cr, uid, ids, context=None):
        """ Return a list of tuples contains id, name.
            result format : {[(id, name), (id, name), ...]}
            
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of ids for which name should be read
            @param context: context arguments, like lang, time zone
            
            @return: returns a list of tupples contains id, name
        """
        # Used for not have destination as: parent (type
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]            
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            res.append((record.id, record.name))
        return res
    
class SaleOrder(orm.Model):
    ''' Manage delivery in header
    '''
    _inherit = 'sale.order'
    
    # Override onchange for reset address name
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(SaleOrder, self).onchange_partner_id(
            cr, uid, ids, part, context=context)
        # Reset value if not present    
        res['value']['destination_partner_id'] = False
        res['value']['invoice_partner_id'] = False
        return res

    _columns = {
        'destination_partner_id': fields.many2one(
            'res.partner', 'Destination'),     
        'invoice_partner_id': fields.many2one(
            'res.partner', 'Invoice'),     
        }

class PurchaseOrder(orm.Model):
    ''' Manage delivery in header
    '''
    _inherit = 'purchase.order'
    
    # Override onchange for reset address name
    #def onchange_partner_id(self, cr, uid, ids, part, context=None):
    #    res = super(SaleOrder, self).onchange_partner_id(
    #        cr, uid, ids, part, context=context)
    #    # Reset value if not present    
    #    res['value']['destination_partner_id'] = False
    #    res['value']['invoice_partner_id'] = False
    #    return res

    _columns = {
        'destination_partner_id': fields.many2one(
            'res.partner', 'Destination'),     
        'invoice_partner_id': fields.many2one(
            'res.partner', 'Invoice'),     
        }

class AccountInvoice(orm.Model):
    ''' Manage delivery in header
    '''
    _inherit = 'account.invoice'
    
    _columns = {
        'destination_partner_id': fields.many2one(
            'res.partner', 'Destination'),     
        'invoice_partner_id': fields.many2one(
            'res.partner', 'Invoice'),     
        }

class StockPicking(orm.Model):
    ''' Manage delivery in header
    '''
    _inherit = 'stock.picking'
    
    _columns = {
        'destination_partner_id': fields.many2one(
            'res.partner', 'Destination'),     
        'invoice_partner_id': fields.many2one(
            'res.partner', 'Invoice'),     
        }

class StockDdt(orm.Model):
    ''' Manage delivery in header
    '''
    _inherit = 'stock.ddt'
    
    _columns = {
        'destination_partner_id': fields.many2one(
            'res.partner', 'Destination'),     
        'invoice_partner_id': fields.many2one(
            'res.partner', 'Invoice'),     
        }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
