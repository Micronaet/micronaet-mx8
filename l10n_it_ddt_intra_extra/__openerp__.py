# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Abstract (http://www.abstract.it)
#    @author Davide Corio <davide.corio@abstract.it>
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

{
    'name': 'DdT extrafields',
    'version': '1.0',
    'category': 'Report',
    'summary': 'Extra field',
    'description': """
        Intra tield
    """,
    'author': 'Nicola Riolini',
    'website': 'https://micronaet.com',
    'depends': [
        'l10n_it_ddt',
        ],
    'data': [
        'views/stock_view.xml',
    ],
    'test': [],
    'installable': True,
    'active': False,
}
