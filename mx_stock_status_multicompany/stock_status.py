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
import pickle
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
        # Default stock locations:
        'stock_location_id': fields.many2one(
            'stock.location', 'Default stock'), 
        'stock_mrp_location_id': fields.many2one(
            'stock.location', 'Default production', 
            help='From movement in/out in production'), 

        # Document for load / unload:
        'stock_report_unload_ids': fields.many2many(
            'stock.picking.type', 'company_picking_out_rel', 
            'company_id', 'type_id', 
            'Pick out type'), 
        'stock_report_load_ids': fields.many2many(
            'stock.picking.type', 'company_picking_in_rel', 
            'company_id', 'type_id', 
            'Pick in type'),
            
        # Document for production in / out:    
        'stock_report_mrp_in_ids': fields.many2many(
            'stock.picking.type', 'company_mrp_in_rel', 
            'company_id', 'type_id', 
            'MRP in type'), 
        'stock_report_mrp_out_ids': fields.many2many(
            'stock.picking.type', 'company_mrp_out_rel', 
            'company_id', 'type_id', 
            'MRP out type'),

        # Exclude partner list:
        'stock_explude_partner_ids': fields.many2many(
            'res.partner', 'company_picking_exclude_partner_rel', 
            'company_id', 'partner_id', 
            'Exclude partner', 
            help='Other company partner ID'), 
            
        'product_mask': fields.char(
            'Mask', size=64, help='Mask for product in other DB'),
        
        # Connection data:
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

    # ----------------------------------------
    # Function called from master DB (transit)
    # ----------------------------------------
    def erpeek_stock_movement_inventory_data(self, cr, uid, product_ids, 
            debug_f):
        ''' Function called by Erpeek with dict passed by pickle file
        '''
        pickle_file = '/home/administrator/photo/dicts.pickle' # TODO 
        debug_file = open(debug_f, 'a')    
        
        pickle_f = open(pickle_file, 'r')        
        dicts = pickle.load(pickle_f)
        pickle_f.close()
        
        res = self.stock_movement_inventory_data(cr, uid, 
            product_ids, True, debug_file, dicts, context=None)

        pickle_f = open(pickle_file, 'w')
        pickle.dump(dicts, pickle_f)
        pickle_f.close()
        debug_file.close()
        return res
            
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
            remote_default_code = []                    
            # List of code found in remote DB
            for p in product_pool.browse(cr, uid, product_ids, 
                    context=context):
                remote_default_code.append(p.default_code)                    
            debug_file.write('\n\nREMOTE CONTROLS:\n') # XXX DEBUG
            
        else:    
            remote_default_code = False    
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

        debug_file.write('\n\nExclude partner list:\n%s\n\n'% (
            exclude_partner_ids,)) # XXX DEBUG
        
        # ---------------------------------------------------------------------
        # Get unload picking BC
        # ---------------------------------------------------------------------
        out_picking_type_ids = []
        if not remote:
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
            debug_file.write('\n\nUnload picking:\nPick;Origin;Code;Q.\n')
            for pick in pick_pool.browse(cr, uid, pick_ids):
                for line in pick.move_lines:
                    default_code = line.product_id.default_code
                    if line.product_id.id in product_ids: # only supplier prod.
                        # TODO check state of line??
                        if default_code not in unloads:
                            unloads[default_code] = line.product_uom_qty
                        else:    
                            unloads[default_code] += line.product_uom_qty
                            
                        debug_file.write('\n%s;%s;%s;%s' % (
                            pick.name, pick.origin, default_code, 
                            line.product_uom_qty)) # XXX DEBUG

        # ---------------------------------------------------------------------
        # Get load picking
        # ---------------------------------------------------------------------
        in_picking_type_ids = []
        if not remote: # XXX No BF for remote
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
                
            debug_file.write('\n\nLoad picking:\nType;Pick;Origin;Code;Q.\n')
            for pick in pick_pool.browse(cr, uid, pick_ids):
                for line in pick.move_lines:
                    if line.product_id.id in product_ids: # only supplier prod.
                        # TODO check state of line??                    
                        default_code = line.product_id.default_code
                        if line.state == 'assigned': # virtual
                            if default_code not in virtual_loads:
                                virtual_loads[default_code] = \
                                    line.product_uom_qty
                            else:    
                                virtual_loads[default_code] += \
                                    line.product_uom_qty

                            debug_file.write('\nOF;%s;%s;%s;%s' % (
                                pick.name, pick.origin, default_code, 
                                line.product_uom_qty)) # XXX DEBUG
                        elif line.state == 'done':
                            if default_code not in loads:
                                loads[default_code] = line.product_uom_qty
                            else:    
                                loads[default_code] += line.product_uom_qty

                            debug_file.write('\nBF;%s;%s;%s;%s' % (
                                pick.name, pick.origin, default_code, 
                                line.product_uom_qty)) # XXX DEBUG
            
        # ---------------------------------------------------------------------
        # Get order to delivery: OC remain
        # ---------------------------------------------------------------------
        sol_ids = sol_pool.search(cr, uid, [
            ('product_id', 'in', product_ids)])
            
        debug_file.write('\n\nOrder remain:\nOrder;Code;Q.\n') # XXX DEBUG
        for line in sol_pool.browse(cr, uid, sol_ids):
            # -------
            # Header:
            # -------            
            # check state (line closed or order not confirmed:            
            if line.order_id.state in (
                    'cancel', 'draft', 'sent') or line.mx_closed:
                debug_file.write('%s;%s;%s\n' % (
                    line.order_id.name, line.product_id.default_code, 
                    'FORCED CLOSE')) 
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
                
            debug_file.write('%s;%s;%s\n' % (
                line.order_id.name, default_code, remain)) # XXX DEBUG
        
        # result is the dicts!        
        if remote:        
            return remote_default_code # for highlight both product
        else:
            return 
    
    def print_stock_status_report_stock(self, cr, uid, ids, context=None):
        ''' Print only present
        '''
        if context is None: 
            context = {}            
        context['only_with_stock'] = True
        return self.print_stock_status_report(
            cr, uid, ids, context=context)
            
    def print_stock_status_report(self, cr, uid, ids, context=None):
        ''' Print report product stock
        '''
        if context is None: 
            context = {}            
                    
        datas = {}
        datas['partner_id'] = ids[0]
        datas['partner_name'] = self.browse(
            cr, uid, ids, context=context)[0].name
        # Mode with esistence or not:    
        datas['only_with_stock'] = context.get('only_with_stock', False)
            
                       
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock_status_multicompany_report',
            'datas': datas,
            }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
