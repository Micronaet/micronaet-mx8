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
                payment_term_id = ddt.payment_term_id.id
                used_bank_id = ddt.used_bank_id.id
                #default_carrier_id                
                #parcels = ddt.parcels # needed?
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

    @api.multi
    def create_invoice(self):
        ddt_model = self.env['stock.ddt']
        picking_pool = self.pool['stock.picking']

        ddts = ddt_model.browse(self.env.context['active_ids'])
        partners = set([ddt.partner_id for ddt in ddts])
        if len(partners) > 1:
            raise Warning(_('Selected DDTs belong to different partners'))
        # TODO check also destination and invoice address?!?!
        pickings = []
        self.check_ddt_data(ddts)
        for ddt in ddts:
            for picking in ddt.picking_ids:
                pickings.append(picking.id)
                #for move in picking.move_lines:
                #    # XXX forced as in done state!!!! 
                #    if move.invoice_state != '2binvoiced':
                #        raise Warning(
                #            _('Move %s is not invoiceable') % move.name)
        invoices = picking_pool.action_invoice_create(
            self.env.cr,
            self.env.uid,
            pickings,
            self.journal_id.id, group=True, context=None)
        
        # Update with extra data taken from DDT elements:    
        invoice_obj = self.env['account.invoice'].browse(invoices)
        invoice_obj.write({
            'carriage_condition_id': ddts[0].carriage_condition_id.id,
            'goods_description_id': ddts[0].goods_description_id.id,
            'transportation_reason_id': ddts[0].transportation_reason_id.id,
            'transportation_method_id': ddts[0].transportation_method_id.id,
            'mx_agent_id': ddts[0].partner_id.agent_id.id,
            'payment_term_id': ddts[0].payment_term_id.id,
            'partner_bank_id': ddts[0].used_bank_id.id,            
            # date?
            # TODO 'parcels': ddts[0].parcels, # calculate            
            })
            
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
