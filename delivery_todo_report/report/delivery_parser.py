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
    last_record = 0
    
    def __init__(self, cr, uid, name, context):
        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_counter': self.get_counter,
            'set_counter': self.set_counter,

            # TODO needed?            
            'product_list': self.product_list,
            'colli_total': self.colli_total,
            'orders': self.order_browse,
            'total_orders': self.total_orders, 
            'is_last': self.is_last,
            'reset_print': self.reset_print,
            'get_telephone': self.get_telephone,
            'get_address_default': self.get_address_default,
        })

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

    def is_last(self, item_id):
        ''' Test if the record id passed is the last of the list
        '''
        if not (item_id and self.last_record):
            return False
        return item_id == self.last_record  # return test value
            
        if value:
            return "%s-%s-%s" % (value[8:10], value[5:7], value[:4])
        return ""        

    def get_italian_date(self, value):
        if value:
            return "%s-%s-%s" % (
                value[8:10],
                value[5:7],
                value[:4])
        return ""
        
    def get_telephone(self, ids):
        if not ids:
           return ""

        partner_proxy = self.pool.get('res.partner').browse(
            self.cr, self.uid, ids)
        #for address in partner_proxy.address:
        #    if not address.mexal_c and not address.mexal_s:
        #       return address.phone
        #return ""
        return partner_proxy.phone

    def get_address_default(self, item_id, partner_name=""):
        ''' Get, from id of partner the first default address imported 
        '''
        if not item_id:
            return ""
        partner_pool = self.pool.get('res.partner')
        partner_proxy = partner_pool.browse(
            self.cr, self.uid, item_id)
        return "%s\n%s\n%s - %s" % (
            partner_proxy.name or '', 
            partner_proxy.street or '', 
            partner_proxy.zip or '', 
            partner_proxy.city or '',
            )

    def reset_print(self):
        ''' Called at the end of report to reset print check
        '''
        header_pool = self.pool.get('statistic.header')
        # Azzero tutte le selezioni (al termine della stampa:
        header_ids = header_pool.search(
            self.cr, self.uid, [('print', '=', True)])
        header_mod = header_pool.write(
            self.cr, self.uid, header_ids, {'print': False})     
        return "" # print nothing    

    def total_orders(self, objects):
        ''' true if the order list is more than one
        '''
        active_ids_list = [x.id for x in objects]        
        order_ids = self.pool.get('statistic.header').search(
            self.cr, self.uid, [('print', '=', True),])
        return len(list(set(active_ids_list + order_ids)) )

    def _get_fully_list(self, objects):
        ''' Return list of object browse id list merged with no replication 
            with al record masked for print 
        '''
        active_ids_list = [x.id for x in objects]        
        order_ids = self.pool.get('statistic.header').search(
            self.cr, self.uid, [('print', '=', True),])
        total_list = list(set(active_ids_list + order_ids))
        return total_list
        
    def order_browse(self, objects):
        ''' Return only in_pricelist product for print a pricelist
        '''
        self.last_record = 0
        
        ids = self._get_fully_list(objects)
        order_proxy = self.pool.get('statistic.header').browse(
            self.cr, self.uid, ids) 
        
        self.last_record = ids[-1] # for extra page
        return order_proxy
        
    def colli_total(self, order_id):
        order_pool = self.pool.get('statistic.order')
        total = 0
        order_line_ids = order_pool.search(
            self.cr, self.uid, [('header_id', '=', order_id)])
        
        for order_line in order_pool.browse(
                self.cr, self.uid, order_line_ids):
            if order_line.colli:
               total += order_line.colli or 0
            else:
               total += order_line.quantity or 0
        return total    

    def product_list(self, objects):
        products = {}
        for order in self.pool.get('statistic.header').browse(
                self.cr, self.uid, self._get_fully_list(objects)):
            for item in order.line_ids:            
                if item.line_type != "d": # only article lines
                    if item.code in products:
                        products[item.code][0] += item.quantity or 0.0
                        products[item.code][1] += item.quantity_ok or 0.0
                        products[item.code][2] = item.article or ""
                    else:          
                        products[item.code] = [
                            item.quantity or 0.0, 
                            item.quantity_ok or 0.0, 
                            item.article or "",
                            ]       
        products_sorted = []       
        for k in sorted(products.iterkeys()):
            products_sorted.append(
                [k, products[k][0], products[k][1], products[k][2]])
        return products_sorted
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
