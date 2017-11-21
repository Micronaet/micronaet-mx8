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
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'    

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def go_check_input_form_mandatory_fields(self, cr, uid, ids, context=None):
        '''
        '''
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, uid, 
            'res_partner_input_form', 
            'view_res_partner_input_form',
            )[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner (campi obbligatori)'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': ids[0],
            'res_model': 'res.partner',
            'view_id': view_id,
            'views': [
                (view_id, 'form'),
                (False, 'tree'),
                ],
            'domain': [('id', '=', ids[0])],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }
        
    def go_partner_normal_form(self, cr, uid, ids, context=None):
        '''
        '''
        #model_pool = self.pool.get('ir.model.data')
        #view_id = model_pool.get_object_reference('module_name', 
        #    'view_name')[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': ids[0],
            'res_model': 'res.partner',
            #'view_id': view_id, # False
            'views': [
                (False, 'form'),
                (False, 'tree'),
                ],
            'domain': [('id', '=', ids[0])],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
