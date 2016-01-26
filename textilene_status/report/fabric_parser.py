#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import sys
import logging
import erppeek
import pickle
from datetime import datetime
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class Parser(report_sxw.rml_parse):
    counters = {}
    headers = {}
    
    def __init__(self, cr, uid, name, context):        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_object': self.get_object,
            'get_filter': self.get_filter
            
            # Utility:
            #'get_counter': self.get_counter,
            #'set_counter': self.set_counter,            
        })

    def get_filter(self, data):
        ''' Get filter selected
        '''
        data = data or {}
        return data.get('partner_name', '')
    
    def get_object(self, data):
        ''' Search all product elements
        '''
        # XXX DEBUG:
        debug_f = '/home/administrator/photo/xls/status.txt'

        # pool used:
        product_pool = self.pool.get('product.product')
        product_ids = product_pool.search(cr, uid, [
            ('default_code', '=ilike', 'T%')], context=context)

        res = []
        for product in product_pool.browse(
                self.cr, self.uid, product_ids):
            # Reset counter for this product    
            inv = product.inventory_start
            tcar = 0.0
            tscar = 0.0
            mm =  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]    
            oc =  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]    
            of =  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]    
            sal = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]    
            
            res.append(
                product, inv, tscar, tcar, mm, oc, of, sal, )
                
        return res
                
        #    raise osv.except_osv(
        #        _('Report error'),
        #        _('No data for this partner',
        #        ))
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
