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
    'name': 'Stock inventory status',
    'version': '0.1',
    'category': 'Report',
    'description': '''        
        Add report for print multi invoice stock inventory
        Remove exhcange of sale form one to other company
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'stock',
        'product',
        'purchase',  # for last purchase date
        'sql_product',  # for stat. cat.
        'close_residual_order',
        'product_image_base',  # for image in report
        'inventory_status',  # stock dispo
        'inventory_field',  # for category
        'csv_import_campaign',  # campaign dispo
        'catalog_management',  # some categorization
        'excel_export',  # Excel report management (for available)
        # 'force_as_corresponding',  # Must be added
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        # 'security/ir.model.access.csv',
        'report/status_report.xml',
        'wizard/print_wizard_view.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
