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
from openerp import models, fields
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

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    def _compute_price(self):
        # ORG:
        #price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        #taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        #self.price_subtotal = taxes['total']
        #if self.invoice_id:
        #    self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)

        total = round(self.price_unit * self.quantity, 2)
        discount = round(total * (self.discount or 0.0) / 100.0, 2)
        st = total - discount

        #discount = round((self.discount or 0.0) / 100.0, 2)
        #price -= discount
        #taxes = self.invoice_line_tax_id.compute_all(
        #    price, self.quantity, product=self.product_id, 
        #    partner=self.invoice_id.partner_id)
        taxes = self.invoice_line_tax_id.compute_all(
            st, 1.0, product=self.product_id, 
            partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(
                self.price_subtotal)
    
    price_subtotal = fields.Float(string='Amount', 
        digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_price')    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
