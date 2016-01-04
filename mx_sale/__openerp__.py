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
    'name': 'MX Sale operation',
    'version': '0.1',
    'category': 'Sale',
    'description': '''        
        Add extra manage for create sale as Mx does
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'stock',
        'sale',
        'sale_stock',
        #'sale_address', # TODO needes?
        
        #'l10n_it_sale', # TODO remove
        'l10n_it_ddt', # TODO keep this only
        'mexal_ddt', # for print button
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        'view/sale_view.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
