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

class AccountInvoice(orm.Model):
    """ Model name: AccountInvoice
    """    
    _inherit = 'account.invoice'

    # -------------------------------------------------------------------------
    # Store function:
    # -------------------------------------------------------------------------
    def send_mail_invoice_marketed_product(self, cr, uid, days=-2, 
            context=None):
        ''' Send mail with line with marketed product for last X days
        '''    
        _logger.info('Launch marketed product invoiced, days: %s' % days)
        #import pdb; pdb.set_trace()
        
        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        WS_name = _('Fatture commercializzati')        
        excel_pool.create_worksheet(WS_name)
        
        # ---------------------------------------------------------------------
        # Format used:
        # ---------------------------------------------------------------------
        title_text = excel_pool.get_format('title')
        header_text = excel_pool.get_format('header')
        row_text = excel_pool.get_format('text')
        
        # ---------------------------------------------------------------------
        # Title:
        # ---------------------------------------------------------------------
        title = 'Prodotti fatturati commercializzati: [Data: %s]' % (
            datetime.now(),
            )

        excel_pool.write_xls_line(
            WS_name, 0, [title, ], default_format=title_text)
        
        # ---------------------------------------------------------------------
        # Header:
        # ---------------------------------------------------------------------
        excel_pool.write_xls_line(
            WS_name, 2, [
                '',
                ], default_format=header_text)
        
        
        
        excel_pool.send_mail_to_group(cr, uid, 
            'outsource_invoice_mail.'
            'group_report_mail_marketed_product_manager',
            'Righe fattura con prodotti commercializzati', 
            'Elenco righe fatture con prodotti commercializzati.', 
            'commercializzati.xlsx', # Mail data
            context=None)
        #group_report_mail_marketed_product_manager
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
