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
    'name': 'Textilene status',
    'version': '0.1',
    'category': 'Report',
    'description': '''
        Manage status report for textilene material
        Use BOM only for this type of product
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'product',
        'mrp',
        'report_aeroo',
        #'report_webkit',
        #'mx_stock_status_multicompany', # TODO change only for parameters comp.
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        'security/xml_groups.xml',
        #'security/ir.model.access.csv',        
        'textilene_views.xml',
        'report/fabric_report.xml',
        'wizard/report_wizard_view.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
