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


class PickingCreateDirectInvoice(models.TransientModel):
    ''' Wizard for create direct invoice from picking, start from wizard 
        that create invoice from ddt documents
    '''

    _name = "picking.create.direct.invoice"
    _rec_name = "journal_id"

    # -------------------------------------------------------------------------
    #                              Table:
    # -------------------------------------------------------------------------
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    date = fields.Date('Date')
    
    def check_picking_data(self, pickings):
        ''' Check that all picking has common elements mandatory:
        '''        
        # TODO control fields for picking
        return # TODO remove <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        
        i = 0
        for picking in pickings:
            i += 1
            if i == 1: # Update with first picking data:
                carriage_condition_id = picking.carriage_condition_id.id                    
                goods_description_id = picking.goods_description_id.id
                transportation_reason_id = picking.transportation_reason_id.id
                transportation_method_id = picking.transportation_method_id.id
                #mx_agent_id = picking.mx_agent_id.id
                payment_term_id = picking.payment_term_id.id
                used_bank_id = picking.used_bank_id.id
                #default_carrier_id                
                #parcels = picking.parcels # needed?
                continue # check second picking 
            
            if picking.carriage_condition_id.id != carriage_condition_id:
                raise Warning(
                    _('Selected pickings have different Carriage Conditions'))
            if picking.goods_description_id.id != goods_description_id:
                raise Warning(
                    _('Selected pickings have different Descriptions of Goods'))
            if picking.transportation_reason_id.id != transportation_reason_id:
                raise Warning(
                    _('Selected pickings have different Transportation Reasons'))
            if picking.transportation_method_id.id != transportation_method_id:
                raise Warning(
                    _('Selected pickings have different Transportation Methods'))
            #if picking.mx_agent_id.id != mx_agent_id:
            #    raise Warning(
            #        _('Selected pickings have different Agent'))
            if picking.payment_term_id.id != payment_term_id:
                raise Warning(
                    _('Selected pickings have different Payment terms'))
            if picking.used_bank_id.id != used_bank_id:
                raise Warning(
                    _('Selected pickings have different bank account'))

    @api.multi
    def create_direct_invoice(self):
        picking_pool = self.pool['stock.picking']
        
        pickings = picking_pool.browse(
            self.env.cr, self.env.uid, self.env.context['active_ids'],
            context=self.env.context)
        partners = set([picking.partner_id for picking in pickings])
        if len(partners) > 1:
            raise Warning(_("Selected pickings belong to different partners"))
        self.check_picking_data(pickings)

        invoices = picking_pool.action_invoice_create(
            self.env.cr, self.env.uid, 
            self.env.context['active_ids'],
            self.journal_id.id, group=True, context=None)
        
        
        if not invoices:
            raise Warning(
                _('Cannot create invoice!'))
            
        # Update backlink in pick:
        pickings.write({'invoice_id': invoices[0]})
        
        # Update extra fields in invoice:
        invoice_obj = self.env['account.invoice'].browse(invoices)        
        invoice_obj.write({
            'carriage_condition_id': 
                pickings[0].carriage_condition_id.id,
            'goods_description_id': 
                pickings[0].goods_description_id.id,
            'transportation_reason_id': 
                pickings[0].transportation_reason_id.id,
            'transportation_method_id': 
                pickings[0].transportation_method_id.id,
            # TODO other fields!    
            #'parcels': pickings[0].parcels,
            })
        
        # -------------------------------------------------------------------------
        # Open new form:    
        # -------------------------------------------------------------------------
        ir_model_data = self.env['ir.model.data']
        form_res = ir_model_data.get_object_reference(
            'account', 'invoice_form')
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
