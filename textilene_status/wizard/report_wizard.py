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


from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)



class ProductProductFabricReportWizard(models.TransientModel):
    ''' Wizard report
    '''
    _name = 'product.product.fabric.report.wizard'

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
