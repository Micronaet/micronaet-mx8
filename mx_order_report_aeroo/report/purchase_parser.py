#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA 'KN dati'.(http://kndati.lv) All Rights Reserved.
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
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse


class Parser(report_sxw.rml_parse):
    counters = {}
    
    def __init__(self, cr, uid, name, context):
        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_counter': self.get_counter,
            'set_counter': self.set_counter,
            'bank': self.get_company_bank,
            'get_supplier_info': self.get_supplier_info,
            'get_vat': self.get_vat,
            })

    def get_vat(self, tax):
        ''' Get vat perc
        '''
        return  tax.description or  tax.description
        
    def get_supplier_info(self, product_proxy, supplier_id):
        ''' Search if supplier is in product supplier list and return 
            code - description used from that partner
            self: instanse of class
            product_proxy product.product browse object
            supplier_id: ID (int) of supplier header document
        '''
        for supplier in product_proxy.seller_ids:
            if supplier_id != supplier.name.id:
                continue 
            return '\n%s%s' % (
                ('%s - ' % supplier.product_code) if supplier.product_code \
                    else '',
                supplier.product_name or '',
                )        
        return ''
        
    def get_company_bank(self, obj, field):
        ''' Short function for readability
        '''
        try:
           return obj.bank_account_company_id.__getattribute__(field)
        except:
            return ''   

    def get_counter(self, name):
        ''' Get counter with name passed (else create an empty)
        '''
        if name not in self.counters:
            self.counters[name] = False
        return self.counters[name]

    def set_counter(self, name, value):
        ''' Set counter with name with value passed
        '''
        self.counters[name] = value
        return '' # empty so no write in module

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
