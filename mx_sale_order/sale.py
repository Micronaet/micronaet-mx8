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


class SaleOrder(orm.Model):
    """ Model name: Sale order
    """
    _inherit = 'sale.order'

    @api.multi
    def action_order_sent(self, ):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        template_pool = self.env['email.template']

        # Normal view without template:
        res = {
            'name': _('Componi Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': self.env.context,
            }

        # ---------------------------------------------------------------------
        # Read default template:
        # ---------------------------------------------------------------------
        template = template_pool.search([
            ('default_send', '=', True),
            ('model', '=', 'sale.order'),
            ])

        if not template: # no default
            # Take the first:
            template = template_pool.search([
                ('model', '=', 'sale.order'),
                ])
            if not template:
                return res
        
        res['context'] = {
            'default_model': 'sale.order',
            'default_res_id': self.id,
            'default_use_template': bool(template),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_use_template': True,
            'default_template_id': template.id,
            }
        return res


    def log_sort_id(self, cr, uid, ids, context=None):
        ''' Log message to test ID order
        '''
        order_proxy = self.browse(cr, uid, ids, context=context)[0]
        _logger.info('>>> Order: %s' % self.pool.get('sale.order.line')._order)
        first = True
        for line in order_proxy.order_line:
            if first:
                first = False
                _logger.warning('\n\n\n*** Order: %s' % line._order)
            try:
                mrp = line.mrp_sequence
            except:
                mrp = ''
            _logger.warning('mrp: %s id: %s sequence: %s code: %s qty: %s'  % (
                mrp,
                line.id,
                line.sequence,
                line.product_id.default_code,
                line.product_uom_qty,
                ))
        return True

class SaleOrderLine(orm.Model):
    """ Model name: Sale order lne
    """
    _inherit = 'sale.order.line'
    _order = 'order_id desc, id'

        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
