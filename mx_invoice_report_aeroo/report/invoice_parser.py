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
import logging
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    counters = {}
    
    def __init__(self, cr, uid, name, context):
        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_counter': self.get_counter,
            'set_counter': self.set_counter,
            'bank': self.get_company_bank,
            'get_partic_description': self.get_partic_description,
            'get_tax_line_invoice':self.get_tax_line_invoice,
            'get_language':self.get_language,
            'get_vector_data': self.get_vector_data,
            
            # Proforma:
            'get_tax_line': self.get_tax_line,
            
            # Utility:
            'return_note': self.return_note,
            
            'check_pick_change': self.check_pick_change,
            'write_reference': self.write_reference,
        })
        self.last_picking = False # TODO is reset all reports?

    def get_vector_data(self, o): 
        ''' Reset parameter used in report 
        '''
        # TODO keep in a common place with DDT one's
        if o.force_vector:
            return o.force_vector or '/'
        elif o.default_carrier_id and o.default_carrier_id.partner_id:
            partner = o.default_carrier_id.partner_id
            return '''%s\n%s\n%s %s %s\nP.IVA: %s Tel.: %s\nN. Albo Trasp.: %s''' % (
                    partner.name or '',
                    partner.street or '',
                    partner.zip or '',
                    partner.city or '',
                    partner.state_id.code or '',
                    partner.vat or '',
                    partner.phone or '',                
                    (partner.transport_number or '/') if \
                        partner.is_vector else '/',
                    )                
        else:
            return '/'            
        
    def check_pick_change(self, l):
        ''' Check if this line has different picking value
        '''
        pick = l.generator_move_id.picking_id
        if not pick.id: # do nothing (old value)
            return False
        if not self.last_picking or self.last_picking != pick:
            self.last_picking = pick # save browse
            return True
        return False    

    def write_reference(self):
        ''' Write reference for change pick
        '''
        try:
            if not self.last_picking.id:
                return _('No ref. ')

            res = ''
            if self.last_picking.ddt_id:
                res += ' DDT: %s ' % self.last_picking.ddt_id.name
            if self.last_picking.sale_id:
                res += _(' Order: %s%s ') % (
                    self.last_picking.sale_id.name,
                    _(' (Your ref.: %s )') % (
                        self.last_picking.sale_id.client_order_ref) \
                        if self.last_picking.sale_id.client_order_ref else '',
                    )
            return res            
        except:
            return _(' Reference error ')

    def return_note(self, note):
        ''' Check if exist and after return \n note
        '''
        try:
            note = note.strip()
            if note:
                return '\n\n%s' % note                 
        except:
            return ''   
    

    def get_partic_description(self, partner_id, product_id):
        ''' Check if partner has partic description
        '''
        # TODO optimize
        partic_pool = self.pool.get('res.partner.product.partic')
        res = ''
        partic_ids = partic_pool.search(self.cr, self.uid, [
            ('product_id', '=', product_id),
            ('partner_id', '=', partner_id),
            ])
        if not partic_ids:
            return res
            
        partic_proxy = partic_pool.browse(self.cr, self.uid, partic_ids)[0]
        res = '%s %s' % (
            partic_proxy.partner_code or '', 
            partic_proxy.partner_description or '',
            )
        return res.strip()

    def get_tax_line(self, sol):
        ''' Tax line for order / proforma invoice        
            self: instance of class
            sol: sale order lines for loop 
        '''
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
        
    def get_tax_line_invoice(self, il):
        ''' Tax line for invoice        
            self: instance of class
            il: sale order lines for loop 
        '''
        res = {}
        for line in il:
            if line.invoice_line_tax_id not in res:
                res[line.invoice_line_tax_id] = [
                    line.price_subtotal, 
                    line.price_subtotal * line.invoice_line_tax_id.amount,
                    ]
            else:
                res[line.invoice_line_tax_id][0] += line.price_subtotal
                res[line.invoice_line_tax_id][1] += line.price_subtotal * \
                    line.invoice_line_tax_id.amount
                    
        return res.iteritems()

    def get_company_bank(self, o, field):
        ''' Short function for readability
        '''
        try:
           return obj.bank_account_company_id.__getattr__(field)
        except:
            return ''   

    def get_counter(self, name):
        ''' Get counter with name passed (else create an empty)
        '''
        if name not in self.counters:
            self.counters[name] = False
        return self.counters[name]

    def set_counter(self, name, value):
        ''' Set counter with name with value passed
        '''
        self.counters[name] = value
        return "" # empty so no write in module
        
    def get_language(self, key, lang):
        ''' Get correct language
        '''

        lang_dict = {
            'en_US': {
                'CLIENTE': 'CUSTOMER',
                'PARTITA IVA': 'VAT N.',
                'DOCUMENTO': 'DOCUMENT',
                'CONDIZIONI DI PAGAMENTO': 'PAYMENT TERMS',
                'NUMERO': 'NUMBER',
                'APPOGGIO BANCARIO': 'BANK DETAILS',
                'DATA': 'DATE',
                'SPETT.LE': 'MESSRS',
                'DESTINATARIO': 'CONSIGNEE',
                'CODICE ARTICOLO': 'ITEM',
                'DESCRIZIONE ARTICOLO': 'DESCRIPTION',
                'COLORE': 'COLOR',
                'Q.TA\'': 'Q.TY',
                'PREZZO UNIT.': 'UNIT PRICE',
                'SCONTO': 'DISCOUNT',
                'IMPORTO': 'AMOUNT',
                'ALIQ': 'RATE',
                'IMPONIBILE': 'TAXABLE',
                'IMPOSTA': 'TAX',
                'VALUTA': 'CURRENCY',
                'SPESE BANCA': 'BANK CHARGES',
                'TOTALE IMPONIBILE': 'TAXABLE TOTAL',
                'TOTALE IMPOSTA': 'TOTAL TAX',
                'TOTALE FATTURA': 'TOTAL INVOICE',
                'CAUSALE TRASPORTO': 'TRANSPORT REASON',
                'DATA INIZIO TRASPORTO': 'START DATE TRANSPORT',
                'FIRMA': 'SIGNATURE',
                'INCARICATO DEL TRASPORTO': 'CARRIER',
                'FIRMA DEL DESTINATARIO': 'RECIPIENT SIGNATURE',
                'NOTE': 'NOTES',
                'MEZZO': 'BY',
                'RIF. ORDINE CLIENTE': 'CUSTOMER ORDER REF.',
                'CONSEGNA (SALVO IMPREVISTI)': 'EXPECTED DELIVERY DATE',
                'AGENTE': 'AGENT',
                },
            'fr_FR': {
                'CLIENTE': 'CLIENT',
                'PARTITA IVA': 'NUMÉRO DE TVA',
                'DOCUMENTO': 'DOCUMENT',
                'CONDIZIONI DI PAGAMENTO': 'CONDITIONS DE PAIEMENT',
                'NUMERO': 'NUMÉRO',
                'APPOGGIO BANCARIO': 'BANCAIRE',
                'DATA': 'DATE',
                'SPETT.LE': 'CHER',
                'DESTINATARIO': 'DESTINATAIRE',
                'CODICE ARTICOLO': "CODE D'ARTICLE",
                'DESCRIZIONE ARTICOLO': 'DESCRIPTION',
                'COLORE': 'COULEUR',
                'Q.TA\'': 'QTÉ',
                'PREZZO UNIT.': 'PRIX UNITAIRE',
                'SCONTO': 'RABAIS',
                'IMPORTO': 'MONTANT',
                'ALIQ': 'POURCENTAGE',
                'IMPONIBILE': 'IMPOSABLE',
                'IMPOSTA': 'IMPOSTE',
                'VALUTA': 'MONNAIE',
                'SPESE BANCA': 'DÉPENSES',
                'TOTALE IMPONIBILE': 'TOTAL IMPOSABLE',
                'TOTALE IMPOSTA': 'TOTAL IMPÔT',
                'TOTALE FATTURA': 'TOTAL FACTURE',
                'CAUSALE TRASPORTO': 'CAUSAL TRANSPORT',
                'DATA INIZIO TRASPORTO': 'DATE DÉBUT TRANSPORT',
                'FIRMA': 'SIGNATURE',
                'INCARICATO DEL TRASPORTO': 'ENGAGÉÈ DU TRANSPORT',
                'FIRMA DEL DESTINATARIO': 'SIGNATURE ALLOCUTAIRE',
                'NOTE': 'NOTES',
                'MEZZO': 'MOYEN',
                'RIF. ORDINE CLIENTE': 'RÉF. COMMANDE CLIENT',
                'CONSEGNA (SALVO IMPREVISTI)': 'LIVRAISON (SAUF IMPRÉVU)',
                'AGENTE': 'AGENT',
                
                }
            }
        
        if key in lang_dict or lang == 'it_IT':
            return key
        
        return lang_dict[lang].get(key, '??')
            
        return self.counters[name]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
