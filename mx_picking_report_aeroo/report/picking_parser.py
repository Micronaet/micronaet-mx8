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
            'get_vector_address': get_vector_address,
            
            # Proforma:
            'get_tax_line': self.get_tax_line,            
        })

    def get_vector_address(self, o):
        ''' return vector address
        '''
        res = ''
        if o.carrier_id:
            res = 'VETTORE: %s' % o.carrier_id.name or ''
            res += '\n%s' % (
                o.carrier_id.partner_id.street
                ) if o.carrier_id.partner_id.street  else ''
            res += '\n %s' % (o.carrier_id.partner_id.zip or '')
            res += ' %s' % (o.carrier_id.partner_id.city or '')
            res += ' %s' % (o.carrier_id.partner_id.state_id.code or '')
            
            res += '\nP.IVA: %s' % o.carrier_id.partner_id.vat
            res += '\nTel: %s' % (o.carrier_id.partner_id.phone or '')
            res += '\nNr. Albo Trasp.: ' % '' # TODO
        return res    

    def get_tax_line(self, sol):
        ''' Tax line for order / proforma invoice        
            self: instance of class
            sol: sale order lines for loop 
        '''
        res = {}
        for line in sol:
            if line.tax_id not in res:
                res[line.tax_id] = [
                    line.price_subtotal, 
                    line.price_subtotal * line.tax_id.amount,
                    ]
            else:
                res[line.tax_id][0] += line.price_subtotal
                res[line.tax_id][1] += line.price_subtotal * \
                    line.tax_id.amount
                    
        return res.iteritems()

    def get_company_bank(self, o, field):
        ''' Short function for readability
        '''
        try:
           return obj.bank_account_company_id.__getattr__(field)
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
        return "" # empty so no write in module

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
