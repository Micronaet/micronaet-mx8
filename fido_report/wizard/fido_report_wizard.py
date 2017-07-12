# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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
import xlsxwriter
import openerp.addons.decimal_precision as dp
from calendar import monthrange
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class PrintReportFIDOWizard(orm.TransientModel):
    ''' Wizard for print FIDO report
    '''
    _name = 'print.report.fido.wizard'

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------    
    def action_print(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        def xls_write_row(WS, row, row_data, format_cell):
            ''' Print line in XLS file            
            '''
            ''' Write line in excel file
            '''
            col = 0
            for item in row_data:
                WS.write(row, col, item, format_cell)
                col += 1
            return True

        if context is None: 
            context = {}
        
        # Pool used:
        payment_pool = self.pool.get('statistic.deadline')
        
        # Read parameters:
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        partner_id = wiz_browse.partner_id.id
        agent_id = wiz_browse.agent_id.id
        #journal_id = wiz_browse.journal_id.id
        with_fido = wiz_browse.with_fido
        from_date = wiz_browse.from_date
        to_date = wiz_browse.to_date
        deadline_from_date = wiz_browse.deadline_from_date
        deadline_to_date = wiz_browse.deadline_to_date

        # ---------------------------------------------------------------------
        # Export XLSX file:
        # ---------------------------------------------------------------------
        xls_filename = '/tmp/fido_report.xlsx'
        _logger.info('Start FIDO payment export on %s' % xls_filename)
        
        # Open file and write header
        WB = xlsxwriter.Workbook(xls_filename)
        WS = WB.add_worksheet(_('Payment'))

        # Format:
        format_title = WB.add_format({
            'bold': True, 
            'font_color': 'black',
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'gray',
            'border': 1,
            #'text_wrap': True,
            })

        format_text_green = WB.add_format({
            'font_name': 'Arial',
            'font_size': 9,
            #'align': 'right',
            'bg_color': 'c1e7b3',
            'border': 1,
            #'num_format': '0.00',
            })        
        format_text_red = WB.add_format({
            'font_name': 'Arial',
            'font_size': 9,
            #'align': 'right',
            'bg_color': '#fba099',
            'border': 1,
            #'num_format': '0.00',
            })        
        format_text_grey = WB.add_format({
            'font_name': 'Arial',
            'font_size': 9,
            #'align': 'right',
            'bg_color': '#e7e7e7',
            'border': 1,
            #'num_format': '0.00',
            })        
        
        header = [
            _('Cliente'), 
            _('Agente'), 
            _('FIDO'), 
            _('FIDO Da'),
            _('FIDO Totale'),
            _('Fattura'), 
            _('Data'), 
            _('Scadenza'),            
            _('Scad. FIDO'), # invoice covered
            _('Importo pag.'),
           ]

        # Column dimension:
        WS.set_column(0, 0, 35)
        WS.set_column(1, 1, 30)
        WS.set_column(2, 2, 4)
        WS.set_column(3, 3, 8)
        WS.set_column(4, 4, 8)
        WS.set_column(5, 5, 11)
        WS.set_column(6, 6, 8)
        WS.set_column(7, 7, 8)
        WS.set_column(8, 8, 8)
        WS.set_column(9, 9, 10)
        
        # Export Header:
        xls_write_row(WS, 0, header, format_title)        
        
        # Export data:
        order = 'invoice_ref'
        domain = [('c_o_s', '=', 'c')] # only customer payment
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if agent_id:
            domain.append(('agent_id', '=', agent_id))
        if with_fido:
            domain.append(('fido_total', '>', 0))
        if from_date:
            domain.append(('invoice_date', '>=', from_date))
        if to_date:     
            domain.append(('invoice_date', '<=', to_date))
        if deadline_from_date:
            domain.append(('deadline', '>=', deadline_from_date))
        if deadline_to_date:     
            domain.append(('deadline', '<=', deadline_to_date))

        payment_ids = payment_pool.search(
            cr, uid, domain, order=order, context=context)        
        now = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)    
        i = 0
        for payment in payment_pool.browse(
                cr, uid, payment_ids, context=context):
            i += 1
            
            # Read parameter:
            fido_deadline = payment.fido_deadline
            has_fido = payment.partner_id.fido_total > 0
            
            # Check format:
            if not has_fido:
                format_current = format_text_grey                
            elif fido_deadline < now:
                format_current = format_text_red
            else:    
                format_current = format_text_green
                
            data = [
                payment.partner_id.name,
                payment.partner_id.agent_id.name or '',

                'X' if has_fido else '',
                payment.partner_id.fido_date or '',
                payment.partner_id.fido_total or '',

                payment.invoice_ref,
                payment.invoice_date, 
                payment.deadline, 
                fido_deadline or '',
                payment.total,
                ]
            xls_write_row(WS, i, data, format_current)

        _logger.info('End FIDO payment export on %s' % xls_filename)
        WB.close()

        attachment_pool = self.pool.get('ir.attachment')
        b64 = open(xls_filename, 'rb').read().encode('base64')
        attachment_id = attachment_pool.create(cr, uid, {
            'name': 'FIDO payment report',
            'datas_fname': 'payment_fido_report.xlsx',
            'type': 'binary',
            'datas': b64,
            'partner_id': 1,
            'res_model':'res.partner',
            'res_id': 1,
            }, context=context)
        
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/saveas?model=ir.attachment&field=datas&'
                'filename_field=datas_fname&id=%s' % attachment_id,
            'target': 'self',
            }   

    _columns = {
        'partner_id': fields.many2one(
            'res.partner', 'Partner'),
        'agent_id': fields.many2one(
            'res.partner', 'Agent'),
        'with_fido': fields.boolean('Customer with FIDO'),    
        'from_date': fields.date('From date'),    
        'to_date': fields.date('To date'),    
        'deadline_from_date': fields.date('From deadline'),
        'deadline_to_date': fields.date('To deadline'),
        }
        
    _defaults = {
        }    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
