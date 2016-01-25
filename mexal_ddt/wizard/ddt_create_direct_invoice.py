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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)



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
                carriage_condition_id = picking.sale_id.carriage_condition_id.id                    
                goods_description_id = picking.sale_id.goods_description_id.id
                transportation_reason_id = picking.sale_id.transportation_reason_id.id
                transportation_method_id = picking.sale_id.transportation_method_id.id
                #mx_agent_id = picking.mx_agent_id.id
                payment_term_id = picking.sale_id.payment_term.id
                used_bank_id = picking.sale_id.bank_account_id.id
                default_carrier_id = picking.sale_id.carrier_id.id
                #parcels = picking.parcels # needed?
                destination_partner_id = picking.sale_id.destination_partner_id
                invoice_partner_id = picking.sale_id.invoice_partner_id
                continue # check second picking 
            
            if picking.sale_id.carriage_condition_id.id != carriage_condition_id:
                raise Warning(
                    _('Selected pickings have different Carriage Conditions'))
            if picking.sale_id.goods_description_id.id != goods_description_id:
                raise Warning(
                    _('Selected pickings have different Descriptions of Goods'))
            if picking.sale_id.transportation_reason_id.id != transportation_reason_id:
                raise Warning(
                    _('Selected pickings have different Transportation Reasons'))
            if picking.sale_id.transportation_method_id.id != transportation_method_id:
                raise Warning(
                    _('Selected pickings have different Transportation Methods'))
            #if picking.mx_agent_id.id != mx_agent_id:
            #    raise Warning(
            #        _('Selected pickings have different Agent'))
            if picking.sale_id.payment_term.id != payment_term_id:
                raise Warning(
                    _('Selected pickings have different Payment terms'))
            if picking.sale_id.bank_account_id.id != used_bank_id:
                raise Warning(
                    _('Selected pickings have different bank account'))
            
            if picking.sale_id.destination_partner_id.id != destination_partner_id:
                raise Warning(
                    _('Selected DDTs have different destination'))
            if picking.sale_id.invoice_partner_id.id != invoice_partner_id:
                raise Warning(
                    _('Selected DDTs have different invoice partner'))
            if picking.sale_id.carrier_id.id != default_carrier_id:
                raise Warning(
                    _('Selected DDTs have different invoice partner'))


    @api.multi
    def create_direct_invoice(self):
        picking_pool = self.pool['stock.picking']
        
        active_ids = self.env.context['active_ids']
        pickings = picking_pool.browse(
            self.env.cr, self.env.uid, active_ids,
            context=self.env.context)
            
        partners = set([picking.partner_id for picking in pickings])
        if len(partners) > 1:
            raise Warning(_('Selected pickings belong to different partners'))
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

        # ---------------------------------------------------------------------
        # Unload pick stock:
        # ---------------------------------------------------------------------
        move_pool = self.pool.get('stock.move')
        todo = []
        for pick in picking_pool.browse(self.env.cr, self.env.uid, active_ids,
                context=self.env.context):
            # confirm all picking
            for move in pick.move_lines:
                if move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
        if todo:
            move_pool.action_done(self.env.cr, self.env.uid, todo, 
                context=self.env.context)
        # ---------------------------------------------------------------------
        
        # Update extra fields in invoice:
        invoice_obj = self.env['account.invoice'].browse(invoices)        
        invoice_obj.write({
            'carriage_condition_id': 
                pickings[0].sale_id.carriage_condition_id.id,
            'goods_description_id': 
                pickings[0].sale_id.goods_description_id.id,
            'transportation_reason_id': 
                pickings[0].sale_id.transportation_reason_id.id,
            'transportation_method_id': 
                pickings[0].sale_id.transportation_method_id.id,

            'payment_term': pickings[0].sale_id.payment_term.id,

            'used_bank_id': pickings[0].sale_id.bank_account_id.id,    
            'default_carrier_id': pickings[0].sale_id.carrier_id.id,                        
            'destination_partner_id': pickings[0].sale_id.destination_partner_id.id,
            'invoice_partner_id': pickings[0].sale_id.invoice_partner_id.id,
            'direct_invoice': True,
            'date_invoice': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            

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
