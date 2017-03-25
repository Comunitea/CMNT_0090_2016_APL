# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

from openerp.addons import decimal_precision as dp

class ProjectProjectEstado(models.Model):
    _name ="project.aplstate"

    name = fields.Char("Estado")


class AccountInvoiceAPL(models.Model):

    _inherit = "account.invoice"

    #analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')

    @api.multi
    def _get_payment(self):
        for invoice in self:
            invoice.paid_date = False
            invoice.amount_paid = 0.00
            if invoice.payment_ids:
                for payment in invoice.payment_ids:
                    invoice.paid_date = payment.payment_date
                    invoice.amount_paid += payment.amount



    analytic_account_id = fields.Many2one('account.analytic.account',
                                      'Analytic Account')

    estimated_date = fields.Date("Fecha prevista")
    payment_date = fields.Date("Fecha pago", compute=_get_payment)
    amount_paid = fields.Float("Importe Pagado", digits=dp.get_precision('Account'), compute=_get_payment)
    endowment_date = fields.Date("Fecha dotacion")
    endowment_amount = fields.Float("Importe dotacion", digits=dp.get_precision('Account'))


class AnalityaccountAPL(models.Model):
    _inherit="account.analytic.account"
    invoice_ids = fields.One2many("account.invoice", "analytic_account_id", string="Facturas asociadas")

class ProjectProjectAPL(models.Model):

    _inherit = 'project.project'

    @api.multi
    def _get_total_amounts(self):

        for project in self:
            project.total_paid = 0
            project.total_endowment = 0
            project.total_invoiced = 0
            project.total_base = 0

            domain = [('analytic_account_id', '=', project.analytic_account_id.id), ('state','in',('pro', 'open', 'paid'))]
            invoices = self.env['account.invoice'].search(domain)
            for invoice in invoices:
                project.total_endowment += invoice.endowment_amount
                project.total_invoiced += invoice.amount_total
                if invoice.payment_ids:
                    for payment in invoice.payment_ids:
                        project.total_paid += payment.amount
                project.total_base += invoice.amount_untaxed


    @api.multi
    def _get_last_invoice_date(self):
        for project in self:

            domain = [('analytic_account_id', '=', project.analytic_account_id.id), ('state', 'in', ('open', 'paid'))]
            last_invoice = self.env['account.invoice'].search(domain, limit=1, order='date_invoice desc')
            if last_invoice:
                project.last_invoice_date = last_invoice.date_invoice



    to_invoice = fields.Boolean('Facturable', default=False)
    to_manage = fields.Boolean('Gestionable', default=False)
    last_invoice_date = fields.Date("Ultima factura", compute=_get_last_invoice_date)


    date_DE= fields.Date("Fecha DE")
    date_CITT = fields.Date("Fecha CITT")
    date_resumen = fields.Date("Fecha resumen")
    date_aperture = fields.Date("Fecha apertura")
    register = fields.Char("Registro")
    ci_per_cent = fields.Float("% CI", default="21")
    amount = fields.Float("Importe", digits=dp.get_precision('Account'))

    total_endowment = fields.Float("Importe dotaciones", digits=dp.get_precision('Account'), compute=_get_total_amounts)
    total_invoiced = fields.Float("Importe emitido", digits=dp.get_precision('Account'), compute=_get_total_amounts)
    total_paid = fields.Float("Importe pagado", digits=dp.get_precision('Account'), compute=_get_total_amounts)
    total_base = fields.Float("Importe previsto", digits=dp.get_precision('Account'), compute=_get_total_amounts)

    apl_state = fields.Many2one("project.aplstate")
    #invoice_ids = fields.One2many("account.invoice", "Facturas asociadas")