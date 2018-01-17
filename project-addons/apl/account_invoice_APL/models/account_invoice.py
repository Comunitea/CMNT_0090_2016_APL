# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.addons import decimal_precision as dp

class AnalityaccountAPL(models.Model):
    _inherit = "account.analytic.account"
    invoice_ids = fields.One2many("account.invoice", "project_id", string="Facturas asociadas")


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.multi
    def _get_payment(self):
        for invoice in self:
            invoice.paid_date = False
            invoice.amount_paid = 0.00
            if invoice.payment_ids:
                for payment in invoice.payment_ids:
                    invoice.payment_date = payment.payment_date
                    invoice.amount_paid += payment.amount

    def _compute_planned_activity_cost(self):
        for account in self:
            for activity in account.project_id.activity_ids:
                account.planned_cost += activity.planned_cost

    @api.model
    def _get_date_end(self):
        if self.project_id:
            search_domain = [('project_id', '=', self.project_id.id), ('date_end', '!=', False)]
            task = self.env['project.task'].search(search_domain, order="date_end desc", limit=1)
            self.date_end = task.date_end if task else False
        else:
            self.date_end = False

    project_id = fields.Many2one('project.project', string="Related Project")
    date_end = fields.Datetime('Estimated end date')
    planned_cost = fields.Float('Planned cost')
    project_user_id = fields.Many2one(related='project_id.user_id')

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')

    estimated_date = fields.Date("Fecha prevista")
    payment_date = fields.Date("Fecha pago", compute=_get_payment)
    amount_paid = fields.Float("Importe Pagado", digits=dp.get_precision('Account'), compute=_get_payment)
    endowment_date = fields.Date("Fecha dotacion")
    endowment_amount = fields.Float("Importe dotacion", digits=dp.get_precision('Account'))

    origin = fields.Char(string='Source Document',
                         help="Reference of the document that produced this invoice.")

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoice, self).default_get(fields)

        return res

    @api.onchange('project_id')
    def onchange_project_id(self):

        #self.planned_cost = self.project_id.planned_cost
        #self.date_end = self.project_id.date_end
        if self.type in ('out_refund', 'out_invoice'):
            self.partner_id = self.project_id.partner_id and self.project_id.partner_id or False


class AccountInvoiceLine(models.Model):

    _inherit = 'account.invoice.line'

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoiceLine, self).default_get(fields)
        return res
