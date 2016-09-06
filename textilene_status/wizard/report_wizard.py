# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Abstract (http://www.abstract.it)
#    Copyright (C) 2014 Agile Business Group (http://www.agilebg.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys
import logging
import openerp
import base64
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp import models, api, fields
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp import SUPERUSER_ID#, api
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)


class ProductProductFabricReportWizard(models.TransientModel):
    ''' Wizard report
    '''
    _name = 'product.product.fabric.report.wizard'
    
    #def send_by_email(self, cr, uid, ids, context=None):
    def save_report(self, cr, uid, ids, context=None):
        ''' Export as file report and send by email
        '''
        # Utility:
        def clean(filename):
            remove = '/\'\\&"!;,?=:-) (%$£'
            for c in remove:
                if ord(c) > 127:
                    continue # jump not ascii char
                filename = filename.replace(c, '_')           
            return filename
            
        # attachment_obj = self.pool.get('ir.attachment')
        partner_pool = self.pool.get('res.partner') # non necessary
        action_pool = self.pool.get('ir.actions.report.xml')
        date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # Parameter:
        report_name = 'custom_mx_invoice_report' #'stock_status_fabric_report'
        
        report_service = 'report.%s' % report_name
        service = netsvc.LocalService(report_service)
        
        # Call report:            
        (result, extension) = service.create(
            cr, uid, [1], {'model': 'account.invoice'}, context=context)
            #cr, uid, [1], {'model': 'res.partner'}, context=context)
            
        # Generate file:    
        #string_pdf = base64.decodestring(result)
        filename = '/tmp/tx_status_%s.%s' % (
            date,
            extension,
            )
        file_pdf = open(filename, 'w')
        file_pdf.write(result)
        file_pdf.close()
        
        # Send mail with attachment:
        group_pool = self.pool.get('res.groups')
        model_pool = self.pool.get('ir.model.data')
        thread_pool = self.pool.get('mail.thread')
        group_id = model_pool.get_object_reference(
            cr, uid, 'textilene_status', 'group_textilene_admin')[1]    
        partner_ids = []
        for user in group_pool.browse(
                cr, uid, group_id, context=context).users:
            partner_ids.append(user.partner_id.id)
        import pdb; pdb.set_trace()
        thread_pool = self.pool.get('res.partner')
        thread_pool.message_post(cr, uid, recipient_partners, 
            type='notification', subtype='mt_comment',
            #type='email',
            body='Textilente status', subject='TX Report: %s' % date,
            partner_ids=[(6, 0, partner_ids)],
            attachments=[('Report.odt', result)], context=context
            )
        #You could pass the argument attachments=[('filename', 'file raw data not encoded with base64')] to message_post                                
        return True
        
    def open_report(self, cr, uid, ids, context=None):
        ''' Open fabric report
        '''
        assert len(ids) == 1, 'Only one wizard record!'
        
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        datas = {}
        
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock_status_fabric_report',
            'datas': datas,
            'context': context,
            }
