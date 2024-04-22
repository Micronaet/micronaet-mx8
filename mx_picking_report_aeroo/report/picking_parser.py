#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.tools.translate import _


class Parser(report_sxw.rml_parse):
    counters = {}

    def __init__(self, cr, uid, name, context):

        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_counter': self.get_counter,
            'set_counter': self.set_counter,
            'bank': self.get_company_bank,
            'get_vector_address': self.get_vector_address,
            'get_language': self.get_language,

            # Proforma:
            'get_tax_line': self.get_tax_line,
        })

    def get_vector_address(self, o):
        """ return vector address
        """
        res = ''
        if o.carrier_id:
            res = _('VETTORE: %s') % o.carrier_id.name or ''
            res += '\n%s' % (
                o.carrier_id.partner_id.street
                ) if o.carrier_id.partner_id.street  else ''
            res += '\n%s' % (
                o.carrier_id.partner_id.zip or '')
            res += ' %s' % (
                o.carrier_id.partner_id.city or '')
            res += ' %s' % (
                o.carrier_id.partner_id.state_id.code or '')

            res += _('\nP.IVA: %s') % (o.carrier_id.partner_id.vat or '')
            res += _('\nTel: %s') % (o.carrier_id.partner_id.phone or '')
            res += _('\nNr. Albo Trasp.: %s') % '' # TODO
        return res

    def get_tax_line(self, sol):
        """ Tax line for order / proforma invoice
            self: instance of class
            sol: sale order lines for loop
        """
        res = {}
        for line in sol:
            if line.tax_id not in res:
                res[line.tax_id] = [
                    line.price_subtotal,
                    line.price_subtotal * line.tax_id.amount,
                    ]
            else:
                res[line.tax_id][0] += line.price_subtotal
                res[line.tax_id][1] += line.price_subtotal * \
                    line.tax_id.amount

        return res.iteritems()

    def get_company_bank(self, obj, field):
        """ Short function for readability
        """
        try:
           return obj.bank_account_company_id.__getattr__(field)
        except:
            return ''

    def get_counter(self, name):
        """ Get counter with name passed (else create an empty)
        """
        if name not in self.counters:
            self.counters[name] = False
        return self.counters[name]

    def set_counter(self, name, value):
        """ Set counter with name with value passed
        """
        self.counters[name] = value
        return ""  # empty so no write in module

    def get_language(self, key, lang):
        """ Get correct language
        """
        lang_dict = {
            'en_US': {
                'CLIENTE': u'CUSTOMER',
                'PARTITA IVA': u'VAT N.',
                'DOCUMENTO': u'DOCUMENT',
                'CONDIZIONI DI PAGAMENTO': u'PAYMENT TERMS',
                'NUMERO': u'NUMBER',
                'APPOGGIO BANCARIO': u'BANK DETAILS',
                'DATA': u'DATE',
                'SPETT.LE': u'MESSRS',
                'DESTINATARIO': u'CONSIGNEE',
                'CODICE ARTICOLO': u'ITEM',
                'DESCRIZIONE ARTICOLO': u'DESCRIPTION',
                'COLORE': u'COLOR',
                'Q.TA\'': u'Q.TY',

                'CAUSALE TRASPORTO': u'REASON OF TRANSPORT',
                'DATA INIZIO TRASPORTO': u'DATE OF TAKING OVER',
                'INCARICATO DEL TRASPORTO': u'TRANSPORT BY',
                'FIRMA DESTINATARIO': "CONSIGNEE'S SIGNATURE",
                'NOTE': u'NOTES',
                'MEZZO': u'BY',
                'RIF. ORDINE CLIENTE': u'CUSTOMER ORDER REF.',
                'CONSEGNA (SALVO IMPREVISTI)': u'EXPECTED DELIVERY DATE',
                'AGENTE': u'AGENT',
                'COD. CLIENTE': u'CUSTOM. REF',
                'TELEFONO DESTINATARIO': "PHONE CONSIGNEE'S",
                'ASPETTO DEI BENI': u'PACKAGE DESCRIPTION',
                'PORTO': u'PORT',
                'N.COLLI': u'PACKAGES',
                },

            'fr_FR': {
                'CLIENTE': u'CLIENT',
                'PARTITA IVA': u'NUMÉRO DE TVA',
                'DOCUMENTO': u'DOCUMENT',
                'CONDIZIONI DI PAGAMENTO': u'CONDITIONS DE PAIEMENT',
                'NUMERO': u'NUMÉRO',
                'APPOGGIO BANCARIO': u'BANCAIRE',
                'DATA': u'DATE',
                'SPETT.LE': u'CHER',
                'DESTINATARIO': u'DESTINATAIRE',
                'CODICE ARTICOLO': "CODE D'ARTICLE",
                'DESCRIZIONE ARTICOLO': u'DESCRIPTION',
                'COLORE': u'COULEUR',
                'Q.TA\'': u'QTÉ',

                'CAUSALE TRASPORTO': u'CAUSAL TRANSPORT',
                'DATA INIZIO TRASPORTO': u'DATE DÉBUT TRANSPORT',
                'FIRMA': u'SIGNATURE',
                'INCARICATO DEL TRASPORTO': u'ENGAGÉÈ DU TRANSPORT',
                'FIRMA DESTINATARIO': u'SIGNATURE ALLOCUTAIRE',
                'NOTE': u'NOTES',
                'MEZZO': u'MOYEN',
                'RIF. ORDINE CLIENTE': u'RÉF. COMMANDE CLIENT',
                'CONSEGNA (SALVO IMPREVISTI)': u'LIVRAISON (SAUF IMPRÉVU)',
                'AGENTE': u'AGENT',

                }
            }

        if key in lang_dict or lang == 'it_IT':
            return key

        return lang_dict[lang].get(key, '??')
        # return self.counters[name]
