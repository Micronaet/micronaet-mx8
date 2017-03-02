# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import erppeek
import sys
import ConfigParser

# -----------------------------------------------------------------------------
#                             Read Parameters:
# -----------------------------------------------------------------------------
cfg_file = 'odoo.cfg' # same directory
config = ConfigParser.ConfigParser()
config.read(cfg_file)

# General parameters:
server = config.get('odoo', 'server')
port = eval(config.get('odoo', 'port'))
database = config.get('odoo', 'database')
user = config.get('odoo', 'user')
password = config.get('odoo', 'password')

# -----------------------------------------------------------------------------
#                               Start procedure:
# -----------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (server, port), 
    db=database, 
    user=user, 
    password=password
    )

# Pool used:
order_pool = odoo.model('sale.order')

# Close all order:
print 'Inizio procedura di aggiornamento ordini:'
#order_pool.scheduled_check_close_order()
# TODO svincolarla dalla procedura di aggiornamento completa
print 'Chiusi gli ordini presenti consegnati'

# Search open order:
order_ids = order_pool.search([
    ('state', 'not in', ('cancel', 'sent', 'draft')),
    ('mx_closed', '=', False),    
    ])
print 'Trovati %s ordini da valutare' % len(order_ids)
    
i = 0
for item_id in order_ids:
    i += 1
    try:
        order_pool.force_parameter_for_delivery_one([item_id])
        print '%s. Ordine aggiornato: %s' % (i, item_id)
    except:
        print '%s. Errore aggiornando: %s' % (i, item_id)
print 'Procedura terminata'
