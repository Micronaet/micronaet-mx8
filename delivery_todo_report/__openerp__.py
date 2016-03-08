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

{
    'name': 'Delivery todo report',
    'version': '0.1',
    'category': 'Report',
    'description': ''' 
        Add print button to sale order for print a list of delivery 
        (and a sort of order for stock user)       
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'sale',
        'sale_delivery_partial',
        'mx_agent',
        'mx_close_order',
        'production_accounting_external',
        'mx_partner_zone',
        'fido_order_check',
        'mx_agent', # agent filter
        'inventory_status_on_delivery',
        #'base_accounting_program', # res.partner.zone TODO move in module!
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        #'security/ir.model.access.csv',    
        'delivery_view.xml',
        'report/delivery_report.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
