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
import smtplib
import ConfigParser
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText
from email import Encoders
from datetime import datetime

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
mailer = odoo.model('ir.mail_server')

# -----------------------------------------------------------------------------
# Close all order:
# -----------------------------------------------------------------------------
"""
print 'Inizio procedura di aggiornamento ordini:'
print 'Chiusi gli ordini presenti consegnati'
order_pool.scheduled_check_close_order()

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
"""
# -----------------------------------------------------------------------------
# Controllo pronti da chiudere
# -----------------------------------------------------------------------------
print 'Controllo ordini pronti da consegnare'
now = ('%s' %datetime.now())[:19]

order_ids = order_pool.search([
    ('state', 'not in', ('cancel', 'sent', 'draft')),
    ('mx_closed', '=', False),    
    ('all_produced', '=', True),
    ])
    
if not order_ids:
    print 'Nessun ordine pronto, procedura terminata'
    sys.exit()
    
print 'Trovati %s ordini da valutare' % len(order_ids)

order_list = '''
    <table>
       <th>
           <td>Ordine</td>
           <td>Data</td>
           <td>Scad.</td>
           <td>Cliente</td>
           <td>Totale</td>
       </th>           
'''

for order in order_pool.browse(order_ids):
    order_list += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
        order.name,
        order.date_confirm or '',
        order.date_deadline or '',
        order.partner_id.name,
        order.amount_total,
        )
order_list += '</table>'

# -----------------------------------------------------------------------------
# Mail:
# -----------------------------------------------------------------------------
smtp = {
    'to': config.get('smtp', 'to'),
    'text': '''
        <p>Spett.li responsabili vendite,</p>
        <p>Questa &egrave; una mail automatica giornaliera inviata da 
            <b>ODOO</b> con lo stato ordini pronti non chiusi.
        </p>

        <p>Situazione aggiornata alla data di riferimento: <b>%s</b></p>
         
        %s 

        <b>Micronaet S.r.l.</b>
        ''' % (now, order_list),
    'subject': 'Dettaglio ordini pronti non chiusi: %s' % now,    
    }

# -----------------------------------------------------------------------------
# SMTP Sent:
# -----------------------------------------------------------------------------
# Get mailserver option:
mailer_ids = mailer.search([
    ('sequence', '=', 5)])
if not mailer_ids:
    print '[ERR] No mail server configured in ODOO'
    sys.exit()

odoo_mailer = mailer.browse(mailer_ids)[0]

# Open connection:
print '[INFO] Sending using "%s" connection [%s:%s]' % (
    odoo_mailer.name,
    odoo_mailer.smtp_host,
    odoo_mailer.smtp_port,
    )

if odoo_mailer.smtp_encryption in ('ssl', 'starttls'):
    smtp_server = smtplib.SMTP_SSL(
        odoo_mailer.smtp_host, odoo_mailer.smtp_port)
else:
    print '[ERR] Connect only SMTP SSL server!'
    sys.exit()
    #server_smtp.start() # TODO Check

smtp_server.login(odoo_mailer.smtp_user, odoo_mailer.smtp_pass)
for to in smtp['to'].replace(' ', '').split(','):
    print 'Senting mail to: %s ...' % to
    msg = MIMEMultipart()
    msg['Subject'] = smtp['subject']
    msg['From'] = odoo_mailer.smtp_user
    msg['To'] = smtp['to'] #', '.join(self.EMAIL_TO)
    msg.attach(MIMEText(smtp['text'], 'html'))
    
    # Send mail:
    smtp_server.sendmail(odoo_mailer.smtp_user, to, msg.as_string())
smtp_server.quit()

print 'Procedura terminata con invio mail ordini pendenti da consegnare'
