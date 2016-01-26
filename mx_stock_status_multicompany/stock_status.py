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


class ResCompany(orm.Model):
    """ Model name: ResCompany
    """    
    _inherit = 'res.company'
    
    _columns = {
        'stock_report_unload_ids': fields.many2many(
            'stock.picking.type', 'company_picking_out_rel', 
            'company_id', 'type_id', 
            'Pick out type'), 
        'stock_report_load_ids': fields.many2many(
            'stock.picking.type', 'company_picking_in_rel', 
            'company_id', 'type_id', 
            'Pick in type'),

        'stock_explude_partner_ids': fields.many2many(
            'res.partner', 'company_picking_exclude_partner_rel', 
            'company_id', 'partner_id', 
            'Exclude partner', 
            help='Other company partner ID'), 
            
        'product_mask': fields.char(
            'Mask', size=64, help='Mask for product in other DB'),
        
        'is_remote_stock': fields.boolean('Is remote company', 
            help='If is remote company no XMLRPC connection'),
        'remote_name': fields.char('XMLRPC DB name', size=80),
        'remote_hostname': fields.char('XMLRPC Hostname', size=80),
        'remote_port': fields.integer('XMLRPC Port'),
        'remote_username': fields.char('XMLRPC Username', size=80),
        'remote_password': fields.char('XMLRPC Password', size=80),
        }

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Utility function for calculate all movement (for remote and master DB)
    # -------------------------------------------------------------------------
    def stock_movement_inventory_data(self, cr, uid, product_ids, remote, 
            debug_file, dicts=None, context=None):
        ''' Calculate all statistic for inventory
            The operation will be processed in this database or in a remote
            master: product_ids = list of ID
            remote: product_ids = list of code so need to be get ID
            inventory: contain all dictionaty used for this calculation
            context: context
        '''
        # Unpack dicts to be used:
        (loads, unloads, orders, virtual_loads) = dicts
        
        # TODO regenerate company_proxt (TODO passed to caller function?!?)
        company_pool = self.pool.get('res.company')
        company_ids = company_pool.search(cr, uid, [], context=context)
        company_proxy = company_pool.browse(
            cr, uid, company_ids, context=context)[0]
        
        # pool used:
        product_pool = self.pool.get('product.product')
        supplier_pool = self.pool.get('product.supplierinfo')
        pick_pool = self.pool.get('stock.picking')
        sale_pool = self.pool.get('sale.order') # XXX maybe not used 
        sol_pool = self.pool.get('sale.order.line') # XXX maybe not used 
        # procurements in stock.picking

        if remote:
            product_ids = product_pool.search(cr, uid, [
                ('default_code', 'in', product_ids)], context=context)
            debug_file.write('\n\nREMOTE CONTROLS:\n') # XXX DEBUG
        else:    
            debug_file.write('\n\nMASTER CONTROLS:\n') # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Parameter for filters:
        # ---------------------------------------------------------------------
        # Exclude partner list:
        exclude_partner_ids = []
        for item in company_proxy.stock_explude_partner_ids:
            exclude_partner_ids.append(item.id)
            
        # Append also this company partner (for inventory)    
        exclude_partner_ids.append(company_proxy.partner_id.id)
        
        # From date:
        from_date = datetime.now().strftime('%Y-01-01 00:00:00')    
        to_date = datetime.now().strftime('%Y-12-31 23:59:59')    

        debug_file.write('\n\nExclude partner list:\n') # XXX DEBUG
        debug_file.write('%s' % (exclude_partner_ids,)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Get unload picking
        # ---------------------------------------------------------------------
        out_picking_type_ids = []
        for item in company_proxy.stock_report_unload_ids:
            out_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(cr, uid, [     
            # type pick filter   
            ('picking_type_id', 'in', out_picking_type_ids),
            # Partner exclusion
            ('partner_id', 'not in', exclude_partner_ids), 
            # TODO check data date
            ('date', '>=', from_date), 
            ('date', '<=', to_date), 
            # TODO state filter
            ])
        debug_file.write('\n\nUnload picking:\n') # XXX  DEBUG           
        for pick in pick_pool.browse(cr, uid, pick_ids):
            debug_file.write('\nPick: %s\n' % pick.name) # XXX DEBUG
            for line in pick.move_lines:
                default_code = line.product_id.default_code
                if line.product_id.id in product_ids: # only supplier prod.
                    # TODO check state of line??
                    if default_code not in unloads:
                        unloads[default_code] = line.product_uom_qty
                    else:    
                        unloads[default_code] += line.product_uom_qty
                        
                    debug_file.write('\nProd.: %s [%s]' % (
                        default_code, line.product_uom_qty)) # XXX DEBUG

        # ---------------------------------------------------------------------
        # Get unload picking
        # ---------------------------------------------------------------------
        in_picking_type_ids = []
        for item in company_proxy.stock_report_load_ids:
            in_picking_type_ids.append(item.id)
            
        pick_ids = pick_pool.search(cr, uid, [     
            # type pick filter   
            ('picking_type_id', 'in', in_picking_type_ids),            
            # Partner exclusion
            ('partner_id', 'not in', exclude_partner_ids),            
            # check data date
            ('date', '>=', from_date), # XXX correct for virtual?
            ('date', '<=', to_date),            
            # TODO state filter
            ])
        debug_file.write('\n\nLoad picking:\n') # XXX DEBUG       
        for pick in pick_pool.browse(cr, uid, pick_ids):
            for line in pick.move_lines:
                if line.product_id.id in product_ids: # only supplier prod.
                    # TODO check state of line??                    
                    default_code = line.product_id.default_code
                    if line.state == 'assigned': # virtual
                        _logger.info('\nOF virtual: %s - %s [%s]\n' % (
                            line.picking_id.name,
                            default_code,
                            line.product_uom_qty,
                            ))
                        if default_code not in loads:
                            virtual_loads[default_code] = line.product_uom_qty
                        else:    
                            virtual_loads[default_code] += line.product_uom_qty
                        debug_file.write('Virtual: %s [%s]\n' % (
                            default_code, line.product_uom_qty)) # XXX DEBUG
                    elif line.state == 'done':
                        _logger.info('OF load: %s - %s [%s]\n' % (
                            line.picking_id.name,
                            default_code,
                            line.product_uom_qty,
                            ))
                        if default_code not in loads:
                            loads[default_code] = line.product_uom_qty
                        else:    
                            loads[default_code] += line.product_uom_qty
                        debug_file.write('Load: %s [%s]\n' % (
                            default_code, line.product_uom_qty)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Get order to delivery
        # ---------------------------------------------------------------------
        sol_ids = sol_pool.search(cr, uid, [
            ('product_id', 'in', product_ids)])
            
        debug_file.write('\n\nOrder remain:\n') # XXX DEBUG
        for line in sol_pool.browse(cr, uid, sol_ids):
            # -------
            # Header:
            # -------            
            # check state:
            if line.order_id.state in ('cancel', 'draft', 'sent'): #done?
                continue
            
            # ------
            # Lines:
            # ------            
            # Check delivered:
            remain = line.product_uom_qty - line.delivered_qty
            if remain <= 0.0:
                continue
            
            default_code = line.product_id.default_code
            if default_code in orders:
                orders[default_code] += remain
            else:
                orders[default_code] = remain
            debug_file.write('Product: %s [%s]\n' % (
                default_code, remain)) # XXX DEBUG
        
        # result is the dicts!        
        if remote:        
            return product_ids # for hignlight both product
        else:
            return 
    
    def print_stock_status_report(self, cr, uid, ids, context=None):
        ''' Print report product stock
        '''
        if context is None: 
            context = {}            
                    
        datas = {}
        datas['partner_id'] = ids[0]
        datas['partner_name'] = self.browse(
            cr, uid, ids, context=context)[0].name
                       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock_status_multicompany_report',
            'datas': datas,
            }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
