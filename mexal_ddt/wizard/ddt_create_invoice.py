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


import logging
from openerp import models, api, fields
from openerp.osv import fields, osv, expression, orm
from openerp.tools.translate import _
from openerp.exceptions import Warning


_logger = logging.getLogger(__name__)

class AccouuntInvoiceLine(orm.Model):
    ''' Account invoice line for link
    '''
    _inherit = 'account.invoice.line'
    
    _columns = {
        'generator_move_id': fields.many2one(
            'stock.move', 'Generator of line (move)'), 
        }

class StockMove(orm.Model):
    ''' Problem: VAT not propagate (procurement not present in my module)
    '''
    _inherit = 'stock.move'

    def _get_moves_taxes(self, cr, uid, moves, inv_type, context=None):
        ''' Override function for use directyl sale_order_id  not procurements:      
        '''
        # TODO check what's extra_move
        is_extra_move, extra_move_tax = super(        
            StockMove, self)._get_moves_taxes(
                cr, uid, moves, inv_type, context=context)
        if inv_type == 'out_invoice':
            for move in moves:
                #XXX 
                #if move.procurement_id and move.procurement_id.sale_line_id:
                if move.sale_line_id:
                    is_extra_move[move.id] = False
                    # XXX move.sale_line_id
                    extra_move_tax[move.picking_id, move.product_id] = [
                        (6, 0, [x.id for x in move.sale_line_id.tax_id])]
                elif move.picking_id.sale_id and \
                        move.product_id.product_tmpl_id.taxes_id:
                    fp = move.picking_id.sale_id.fiscal_position
                    res = self.pool.get('account.invoice.line'
                        ).product_id_change(
                            cr, uid, [], move.product_id.id, None, 
                            partner_id=move.picking_id.partner_id.id, 
                            fposition_id=(fp and fp.id), 
                            context=context)
                    extra_move_tax[0, move.product_id] = [
                        (6, 0, res['value']['invoice_line_tax_id'])]
                else:
                    extra_move_tax[0, move.product_id] = [
                        (6, 0, [x.id for x in \
                            move.product_id.product_tmpl_id.taxes_id])]
        return (is_extra_move, extra_move_tax)


class stock_picking(osv.osv):
    ''' Problem: VAT not propagate (procurement not present in my module)
        TODO copy as is maybe revomable!!
    '''
    _inherit = 'stock.picking'

    # Override function:
    def _invoice_create_line(self, cr, uid, moves, journal_id, 
            inv_type='out_invoice', context=None):
        ''' Create invoice line from picking (direct invoice of DDT invoice)
        '''    
        
        # Pool used:    
        invoice_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        move_obj = self.pool.get('stock.move')
        
        invoices = {}
        is_extra_move, extra_move_tax = move_obj._get_moves_taxes(
            cr, uid, moves, inv_type, context=context)
            
        product_price_unit = {}
        # TODO check order line here!!!
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            _logger.info('>>> Invoicing picking: %s [%s]' % (
                origin, move.id))
            partner, user_id, currency_id = move_obj._get_master_data(
                cr, uid, move, company, context=context)

            key = (partner, currency_id, company.id, uid) # XXX ex user_id
            invoice_vals = self._get_invoice_vals(
                cr, uid, key, inv_type, journal_id, move, context=context)

            if key not in invoices:
                # Get account and payment terms
                invoice_id = self._create_invoice_from_picking(
                    cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id
            else:
                invoice = invoice_obj.browse(
                    cr, uid, invoices[key], context=context)
                if not invoice.origin or invoice_vals['origin'] not in \
                        invoice.origin.split(', '):
                    invoice_origin = filter(
                        None, [invoice.origin, invoice_vals['origin']])
                    invoice.write(
                        {'origin': ', '.join(invoice_origin)})

            invoice_line_vals = move_obj._get_invoice_line_vals(
                cr, uid, move, partner, inv_type, context=context)
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin
            
            #  TODO what's is_extra_move?
            if not is_extra_move[move.id]:
                product_price_unit[
                    invoice_line_vals['product_id']] = invoice_line_vals[
                        'price_unit']
            if is_extra_move[move.id] and invoice_line_vals[
                    'product_id'] in product_price_unit:
                invoice_line_vals['price_unit'] = \
                    product_price_unit[invoice_line_vals['product_id']]
            # XXX remove: is_extra_move[move.id] and TODO correct???        
            if extra_move_tax[move.picking_id, move.product_id]: 
                invoice_line_vals['invoice_line_tax_id'] = \
                    extra_move_tax[move.picking_id, move.product_id]
            
            # Add extra data from order:
            # TODO manage this value if direct picking invoice / DDT
            if move.sale_line_id:
                # Update discount from order
                invoice_line_vals['discount'] = move.sale_line_id.discount
                invoice_line_vals['multi_discount_rates'] = \
                    move.sale_line_id.multi_discount_rates
                
                # Update price from order
                invoice_line_vals['price_unit'] = move.sale_line_id.price_unit
                # TODO sequence if present!!!
                
            inv_line_id = move_obj._create_invoice_line_from_vals(
                cr, uid, move, invoice_line_vals, context=context)
                
            # Update invoice line with extra data:
            inv_line_obj.write(cr, uid, inv_line_id, {
                'text_note_pre': move.text_note_pre,
                'text_note_post': move.text_note_post,
                'use_text_description': move.use_text_description,                
                'generator_move_id': move.id,
                # TODO: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                # DDT ref.
                # Order ref from pick:
                }, context=context)
            
            move_obj.write(cr, uid, move.id, {
                'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(
            cr, uid, invoices.values(), context=context, 
            set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()
    
class DdTCreateInvoice(models.TransientModel):

    _inherit = 'ddt.create.invoice'

    # -------------------------------------------------------------------------
    # Override 
    # -------------------------------------------------------------------------
    # original function in l10n_it_ddt module for check and update more things:
    def check_ddt_data(self, ddts):
        ''' Check that all DDT has common elements mandatory:
        '''        
        i = 0
        for ddt in ddts:
            i += 1
            if i == 1: # Update with first DDT data:
                carriage_condition_id = ddt.carriage_condition_id.id                    
                goods_description_id = ddt.goods_description_id.id
                transportation_reason_id = ddt.transportation_reason_id.id
                transportation_method_id = ddt.transportation_method_id.id
                #mx_agent_id = ddt.mx_agent_id.id
                #parcels = ddt.parcels # needed?
                
                payment_term_id = ddt.payment_term_id.id
                used_bank_id = ddt.used_bank_id.id
                default_carrier_id = ddt.default_carrier_id.id
                destination_partner_id = ddt.destination_partner_id.id
                invoice_partner_id = ddt.invoice_partner_id.id
                continue # check second DDT 
            
            if ddt.carriage_condition_id.id != carriage_condition_id:
                raise Warning(
                    _('Selected DDTs have different Carriage Conditions'))
            if ddt.goods_description_id.id != goods_description_id:
                raise Warning(
                    _('Selected DDTs have different Descriptions of Goods'))
            if ddt.transportation_reason_id.id != transportation_reason_id:
                raise Warning(
                    _('Selected DDTs have different Transportation Reasons'))
            if ddt.transportation_method_id.id != transportation_method_id:
                raise Warning(
                    _('Selected DDTs have different Transportation Methods'))
            #if ddt.mx_agent_id.id != mx_agent_id:
            #    raise Warning(
            #        _('Selected DDTs have different Agent'))
            
            if ddt.payment_term_id.id != payment_term_id:
                raise Warning(
                    _('Selected DDTs have different Payment terms'))
            if ddt.used_bank_id.id != used_bank_id:
                raise Warning(
                    _('Selected DDTs have different bank account'))
            if ddt.destination_partner_id.id != destination_partner_id:
                raise Warning(
                    _('Selected DDTs have different destination'))
            if ddt.invoice_partner_id.id != invoice_partner_id:
                raise Warning(
                    _('Selected DDTs have different invoice partner'))

    @api.multi
    def create_invoice(self):
        ''' Override original metho in l10n_it_ddt for correct with extra field
        '''
        # Pool used:
        ddt_model = self.env['stock.ddt']
        picking_pool = self.pool['stock.picking']
        invoice_line_pool = self.pool['account.invoice.line']

        ddts = ddt_model.browse(self.env.context['active_ids'])
        partners = set([ddt.partner_id for ddt in ddts])
        if len(partners) > 1:
            raise Warning(_('Selected DDTs belong to different partners'))

        # TODO check also destination and invoice address?!?!
        pickings = []
        self.check_ddt_data(ddts)
        
        # TODO check if there's some DDT yet invoiced!!!
        note_pre = ''
        note_post = ''
        for ddt in ddts:
            if ddt.invoice_id:
                raise Warning(_('There\' DDT yet invoiced: %s') % ddt.number)
                
            for picking in ddt.picking_ids:
                pickings.append(picking.id)
                #for move in picking.move_lines:
                #    # XXX forced as in done state!!!! 
                #    if move.invoice_state != '2binvoiced':
                #        raise Warning(
                #            _('Move %s is not invoiceable') % move.name)
        import pdb; pdb.set_trace()
        invoices = picking_pool.action_invoice_create(
            self.env.cr,
            self.env.uid,
            pickings, # invoice this picking <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            self.journal_id.id, group=True, context=None)
 
        # Save invoice created in ddt document (to no reinvoice again)
        if not invoices:
            raise Warning('No invoice created!!!')
            return # XXX error!!
            
        ddts.write({'invoice_id': invoices[0]})
                
        # ---------------------------------------------------------------------
        #                          Add extra fields:
        # ---------------------------------------------------------------------
        # -------
        # HEADER:
        # -------
        
        # TODO complete with correct fields (from first DDT):
        invoice_obj = self.env['account.invoice'].browse(invoices)
        invoice_obj.write({        
            'carriage_condition_id': ddts[0].carriage_condition_id.id,
            'goods_description_id': ddts[0].goods_description_id.id,
            'transportation_reason_id': ddts[0].transportation_reason_id.id,
            'transportation_method_id': ddts[0].transportation_method_id.id,
            'mx_agent_id': ddts[0].partner_id.agent_id.id,

            #'payment_term_id': ddts[0].payment_term_id.id, # TODO remove?
            'payment_term': ddts[0].payment_term_id.id,

            'partner_bank_id': ddts[0].used_bank_id.id,    
            'used_bank_id': ddts[0].used_bank_id.id, # TODO remove?        

            'default_carrier_id': ddts[0].default_carrier_id.id,
                        
            'destination_partner_id': ddts[0].destination_partner_id.id,
            'invoice_partner_id': ddts[0].invoice_partner_id.id,
            'direct_invoice': False,
                        
            # date?
            # TODO 'parcels': ddts[0].parcels, # calculate            
            })
            
        # ------
        # LINES:
        # ------
            
        # Update line with tax and prices:    
        #for invoice in invoice_obj:
        #    for line in invoice.invoice_line:
        #        tax_ids = line.sale_id.tax_ids
        #        invoice_line_pool.write(cr, uid, line.id, {
        #            'invoice_line_tax_id': [(6, 0, tax_ids)]
        #            #'price_unit': ,
        #            }, context=context)        
            
        # ----------------------
        # Open new invoice form:    
        # ----------------------
        ir_model_data = self.env['ir.model.data']
        form_res = ir_model_data.get_object_reference(
            'account', 'invoice_form',)
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(
            'account', 'invoice_tree')
        tree_id = tree_res and tree_res[1] or False
        return {
            'name': 'Invoice',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': invoices[0],
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'type': 'ir.actions.act_window',
            }
