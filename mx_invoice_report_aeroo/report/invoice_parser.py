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
from openerp.osv import fields, osv, expression, orm
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)


class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'

    def _xmlrpc_get_partic_description(self, cr, uid, product_id,
            partner_id, context=None):
        """ Get partic description
        """
        # TODO optimize
        partic_pool = self.pool.get('res.partner.product.partic')
        res = ''
        partic_ids = partic_pool.search(cr, uid, [
            ('product_id', '=', product_id),
            ('partner_id', '=', partner_id),
            ])
        if not partic_ids:
            return res

        partic_proxy = partic_pool.browse(
            cr, uid, partic_ids, context=context)[0]
        res = '%s %s' % (
            partic_proxy.partner_code or '',
            partic_proxy.partner_description or '',
            )
        return res.strip()


class StockPicking(orm.Model):
    """ Model name: StockPicking
    """

    _inherit = 'stock.picking'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def _parser_template_substitute(self, invoice, data):
        """ Replace data passed with invoice data
        """
        if not data:
            return data

        data = data.replace('{date_invoice}', invoice.date_invoice)
        # TODO other substitution?
        return data

    def write_reference_from_picking(self, picking):
        """ Extract row reference for picking passed
        """
        try:
            if not picking:
                return _('No ref. ')

            res = ''
            if picking.ddt_id:
                # Same name as DDT report:
                name = picking.ddt_id.name
                name_ids = name.split('/')
                if len(name_ids) == 4 and name_ids[2].startswith('2'):# and \
                    if len(name_ids[2]) == 5: # 2016S mode season
                        name_ids.append('S')

                    del(name_ids[2])
                    name = '/'.join(name_ids)

                name = name.lstrip('BC/')
                res += ' DDT: %s (%s/%s/%s) ' % (
                    name,
                    picking.ddt_id.date[8:10],
                    picking.ddt_id.date[5:7],
                    picking.ddt_id.date[0:4],
                    )
            if picking.sale_id:
                res += _(' Order: %s%s ') % (
                    picking.sale_id.name,
                    _(' (Your ref.: %s )') % (
                        picking.sale_id.client_order_ref) \
                        if picking.sale_id.client_order_ref else '',
                    )
            return res
        except:
            return _(' Reference error ')


class Parser(report_sxw.rml_parse):
    counters = {}

    def __init__(self, cr, uid, name, context):

        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_counter': self.get_counter,
            'set_counter': self.set_counter,
            'get_line_number': self.get_line_number,
            'bank': self.get_company_bank,
            'get_partic_description': self.get_partic_description,
            'get_tax_line_invoice':self.get_tax_line_invoice,
            'get_language':self.get_language,
            'get_vector_data': self.get_vector_data,
            'relink_order': self.relink_order,
            'proforma_mode': self.proforma_mode,
            'get_imponibile_mode': self.get_imponibile_mode,
            'template_substitute': self.template_substitute,

            #Intra CEE management:
            'has_intra_cee_page': self.has_intra_cee_page,
            'intra_cee_total_pallet': self.intra_cee_total_pallet,

            # Proforma:
            'get_tax_line': self.get_tax_line,

            # Utility:
            'return_note': self.return_note,

            # OC, DDT, OC customer ref DATA:
            'check_pick_change': self.check_pick_change,
            'write_reference': self.write_reference,
        })
        self.last_picking = False  # TODO is reset all reports?

    def has_intra_cee_page(self, invoice):
        """ Check if need extra CEE page
        """
        # TODO check here if needed
        return True

    def intra_cee_total_pallet(self, invoice):
        """ Check if need extra CEE page
        """
        return sum([
            line.quantity for line in invoice.invoice_line if
            line.product_id.is_pallet])

    def template_substitute(self, invoice, data):
        """ Replace data passed with invoice data
        """
        return self.pool.get('stock.picking')._parser_template_substitute(
            invoice, data)

    def get_line_number(self, reset=False):
        """ Get total line or reset number
        """
        if reset:
            self._line_counter = 0
            return ''
        else:
            self._line_counter += 1
            return self._line_counter

    def get_imponibile_mode(self, o):
        """ Procedure for net total with remain
        """
        total = 0
        for l in o.order_line:
            total += (l.product_uom_qty - l.delivered_qty) * l.price_unit * (
                100.0 - l.discount) / 100.0
        return total

    def proforma_mode(self, ):
        """ Order all or remain ?
        """
        if self.name == 'custom_mx_profora_invoice_remain_report':
            return 'remain'
        else:
            return 'order'

    def relink_order(self, o):
        """ Force for all invoice picking relink to sale order if present
        """
        pick_ids = [item.id for item in o.invoiced_picking_ids]
        if pick_ids:
            _logger.warning('Relink order')
            self.pool.get('stock.picking').link_sale_id(
                self.cr, self.uid, pick_ids)
        else:
            _logger.warning('No picking to relink')

        return ''

    def get_vector_data(self, o):
        """ Reset parameter used in report
        """
        # TODO keep in a common place with DDT one's
        if o.force_vector:
            return o.force_vector or ''
        elif o.default_carrier_id and o.default_carrier_id.partner_id:
            partner = o.default_carrier_id.partner_id
            return '''%s\n%s - %s %s %s\nP.IVA: %s Tel.: %s - N. Albo Trasp.: %s''' % (
                    partner.name or '',
                    partner.street or '',
                    partner.zip or '',
                    partner.city or '',
                    partner.state_id.code or '',
                    partner.vat or '',
                    partner.phone or '',
                    (partner.transport_number or '') if \
                        partner.is_vector else '',
                    )
        else:
            return ''

    def check_pick_change(self, l):
        """ Check if this line has different picking value
        """
        pick = l.generator_move_id.picking_id
        if not pick.id: # do nothing (old value)
            return False
        if not self.last_picking or self.last_picking != pick:
            self.last_picking = pick # save browse
            return True
        return False

    def write_reference(self):
        """ Write reference for change pick
        """
        return self.pool.get('stock.picking').write_reference_from_picking(
            self.last_picking)

    def return_note(self, note):
        """ Check if exist and after return \n note
        """
        try:
            note = note.strip()
            if note:
                return '\n%s' % note
        except:
            return ''


    def get_partic_description(self, partner_id, product_id):
        """ Check if partner has partic description
        """
        return self.pool.get('product.product')._xmlrpc_get_partic_description(
            self.cr, self.uid, product_id, partner_id)

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

    def get_tax_line_invoice(self, il):
        """ Tax line for invoice
            self: instance of class
            il: sale order lines for loop
        """
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
        """ Short function for readability
        """
        try:
           return obj.bank_account_company_id.__getattr__(field)
        except:
            return ''

    def reset_counter(self):
        _logger.info('Counter reset for company 1 load report')
        # reset counters:
        self.counters = {
            'volume': 0.0,
            'length': 0.0,
            'weight': 0.0,
            }
        _logger.info('Counter: %s' % self.counters)
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
        return "" # empty so no write in module



    def get_language(self, key, lang):
        """ Get correct language
        """

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
                'RES.': 'REM.',
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
                'COD. CLIENTE': 'CUSTOM. REF',
                'PORTO': 'PORT',
                'COLLI': 'CARTONS',
                'LUNGHEZZA (LMT)': 'LENGTH (LMT)',
                'PESO': 'WEIGHT',
                'I NOSTRI PRODOTTI SONO STUDIATI E PREVISTI PER USO DOMESTICO. EVENTUALI VENDITE EFFETTUATE AD UTENTI PROFESSIONISTI (ES. BAR, RISTORANTI, DISCOTECHE, PISCINE, ECC.) COMPORTANO LA DECADENZA DI QUALSIASI GARANZIA SUL PRODOTTO.': 'OUR PRODUCTS ARE STUDIED AND DEVELOPED FOR DOMESTIC USE. ANY SALE TO PROFESSIONALS (EX. BARS, RESTAURANTS, CLUBS, SWIMMING POOLS, ETC.) WILL RESULT IN THE DECLINE OF ANY PRODUCT WARRANTY.',
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
                'RES.': 'RES.',
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
                'COD. CLIENTE': 'CODE CLIENT',
                'PORTO': 'PORT',
                'COLLI': 'CARTONS',
                'I NOSTRI PRODOTTI SONO STUDIATI E PREVISTI PER USO DOMESTICO. EVENTUALI VENDITE EFFETTUATE AD UTENTI PROFESSIONISTI (ES. BAR, RISTORANTI, DISCOTECHE, PISCINE, ECC.) COMPORTANO LA DECADENZA DI QUALSIASI GARANZIA SUL PRODOTTO.': 'OUR PRODUCTS ARE STUDIED AND DEVELOPED FOR DOMESTIC USE. ANY SALE TO PROFESSIONALS (EX. BARS, RESTAURANTS, CLUBS, SWIMMING POOLS, ETC.) WILL RESULT IN THE DECLINE OF ANY PRODUCT WARRANTY.',
                }
            }

        if key in lang_dict or lang == 'it_IT':
            return key

        return lang_dict[lang].get(key, '??')

        return self.counters[name]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
