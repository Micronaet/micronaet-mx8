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
import logging
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from datetime import datetime, timedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    counters = {}
    last_record_id = 0
    
    def __init__(self, cr, uid, name, context):
        
        super(Parser, self).__init__(cr, uid, name, context)
        
        self.localcontext.update({
            # counter manage:
            'reset_counter': self.reset_counter,
            'get_counter': self.get_counter,
            'set_counter': self.set_counter,
            'get_last_record_id': self.get_last_record_id,

            'get_object_line': self.get_object_line,
            'get_datetime': self.get_datetime,
            'get_datetime_now': self.get_datetime_now,
            'get_partic': self.get_partic,
            'get_parcels': self.get_parcels,
            'get_parcels_table_load': self.get_parcels_table_load,

            'set_total_parcel': self.set_total_parcel,
            'get_total_parcel': self.get_total_parcel,

            'reset_print': self.reset_print,
            
            'get_order_selected': self.get_order_selected,
        })
        self.reset_counter()
        # TODO remove        
        self.total_parcel = 0.0

    def get_last_record_id(self):
        return self.last_record_id
        
    # -------------------------------------------------------------------------
    #                              COUNTER MANAGE
    # -------------------------------------------------------------------------
    
    def reset_counter(self):
        _logger.info('Counter reset for company 1 load report')
        # reset counters:
        self.counters = {
            'total_parcel': 0.0,
            'volume': 0.0,
            'volume10': 0.0,
            'length': 0.0,
            'weight': 0.0,
            }
        _logger.info('Counter: %s' % self.counters)
        return ''    
            
    def get_counter(self, name):
        ''' Get counter with name passed (else create an empty)
        '''
        if name not in self.counters:
            self.counters[name] = 0.0
        return self.counters[name]

    def set_counter(self, name, value):
        ''' Set counter with name with value passed
        '''
        self.counters[name] = value
        return "" # empty so no write in module

    def set_total_parcel(self, v):
        self.total_parcel = v

    def get_total_parcel(self, ):
        return self.total_parcel or 0.0
        

    def get_parcels(self, product, qty):
        ''' Get text for parcels totals:
            product: proxy obj for product
            qty: total to parcels
        '''
        res = ''
        q_x_pack = product.q_x_pack
        if q_x_pack:
            parcel = qty / q_x_pack
            if not parcel:
                res = ''
            else:
                res = 'SC. %s x %s =' % (int(parcel), int(q_x_pack))
        return res

    def get_parcels_table_load(self, l): #product, qty):
        ''' Get text for parcels totals:
            product: proxy obj for product
            qty: total to parcels
        '''
        res = []
        elements = {
            'S': l.delivery_s, #remain, 
            'B': l.delivery_b,
            }
                
        _logger.info('Element for company 1 load report %s: %s' % (
            elements,
            l.product_id.default_code,
            ))  
        parcel_text = ''          
        for key, v in elements.iteritems():
            product = l.product_id
            if v:
                # Counter totals:
                # TODO volume from dimension (pack or piece?)
                self.counters['volume'] += v * (product.volume or 0.0)
                self.counters['volume10'] += v * (
                    (product.volume or 0.0) * 1.1)
                self.counters['length'] += v* (product.linear_length or 0.0)
                self.counters['weight'] += \
                    v * ((product.weight or 0.0) or (
                        product.weight_net or 0.0))

                q_x_pack = l.product_id.q_x_pack
                partial = False                    
                if q_x_pack:
                    parcel = v / q_x_pack # truncated
                    if v % q_x_pack != 0:
                        partial = True
                        parcel += 1
                    
                    if parcel:
                        parcel_text = 'SC. %sx%s=' % (
                            '??' if partial else int(
                                parcel), 
                            int(q_x_pack),
                            )
                        if not partial:    
                            self.counters['total_parcel'] += parcel
                    else:
                        parcel_text = ''
                res.append((key, parcel_text, v, partial))
                _logger.info('Counters: %s, %s' % (
                    product.default_code,
                    self.counters, 
                    ))
        return res

    def get_partic(self, line):
        ''' Return return if present partner-product partic code
        '''
        partic_pool = self.pool.get('res.partner.product.partic')
        partic_ids = partic_pool.search(self.cr, self.uid, [
            ('partner_id', '=', line.order_id.partner_id.id),
            ('product_id', '=', line.product_id.id),
            ])
        if partic_ids: 
            partic_proxy = partic_pool.browse(self.cr, self.uid, partic_ids)[0]
            return partic_proxy.partner_code or '/'
        return ''#'???'

    def get_datetime(self):
        ''' Return datetime obj
        '''
        return datetime

    def get_datetime_now(self):
        ''' Return datetime obj
        '''
        return datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _get_fully_list(self, objects):
        ''' Return list of object browse id list merged with no replication 
            with al record masked for print 
        '''
        sale_pool = self.pool.get('sale.order')
        
        # Selection by check:
        active_ids = [x.id for x in objects]        

        # Selection by button:
        print_ids = sale_pool.search(self.cr, self.uid, [
            ('print', '=', True)])

        active_ids.extend(print_ids)    
        res = list(set(active_ids))

        # Order per deadline:
        return sale_pool.search(self.cr, self.uid, [
            ('id', 'in', res)], order='date_deadline')

    def get_order_selected(self, objects):
        sale_pool = self.pool.get('sale.order')
        
        res = sale_pool.browse(
            self.cr, self.uid, self._get_fully_list(objects))
        try:
            self.last_record_id = res[-1].id
        except:
            self.last_record_id = 0
        return res    

    def get_object_line(self, objects):
        ''' Selected object + print object
        '''
        products = {}
        res = []
        sale_pool = self.pool.get('sale.order')
                
        for order in sale_pool.browse(
                self.cr, self.uid, self._get_fully_list(objects)):
 
            for line in order.order_line:
                # TODO parametrize (jump delivered all):
                if line.product_uom_qty - line.delivered_qty == 0:
                    continue
                code = line.product_id.default_code
                if code not in products:
                    products[code] = []
                    
                #res.append(line) # unsorted
                products[code].append(line)
        
        # create a res order by product code
        for code in sorted(products):
            res.extend(products[code])        
        return res
        
    def reset_print(self):
        ''' Called at the end of report to reset print check
        '''
        sale_pool = self.pool.get('sale.order')
        sale_pool.reset_print(self.cr, self.uid, False)
        _logger.info('Reset selection')
        return ''

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
