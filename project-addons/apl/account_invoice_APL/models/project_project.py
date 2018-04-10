# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.addons import decimal_precision as dp

class ProjectProjectEstado(models.Model):
    _name ="project.aplstate"

    name = fields.Char("Estado")


class ProjectInvoiceType(models.Model):

    _name ="project.invoice.type"

    name = fields.Char("Tipo")

class ProjectProject(models.Model):

    _inherit = 'project.project'

    @api.multi
    def _get_purchase_invoice_count(self):

        for project in self:
            domain = [('project_id', '=', project.id), ('type', 'in', ('in_refund', 'in_invoice'))]
            project.purchase_invoice_count = len(self.env['account.invoice'].search(domain))

    @api.multi
    def _get_invoice_count(self):
        for project in self:
            domain = [('project_id', '=', project.id), ('type', 'in', ('out_refund', 'out_invoice'))]
            project.invoice_count = len(self.env['account.invoice'].search(domain))

    @api.multi
    def _get_totals(self):

        for project in self:
            sum_amount = 0
            sum_total_base = 0
            sum_project_invoice_cost = 0
            sum_project_cost_balance = 0
            sum_project_cost_balance_base = 0
            for sub in project.child_project_ids_plus:
                sum_amount += sub.amount
                sum_total_base += sub.total_base
                sum_project_invoice_cost += sub.project_invoice_cost
                sum_project_cost_balance += sub.project_cost_balance
                sum_project_cost_balance_base += sub.project_cost_balance_base

            project.sum_amount = sum_amount
            project.sum_total_base = sum_total_base
            project.sum_project_invoice_cost = sum_project_invoice_cost
            project.sum_project_cost_balance = sum_project_cost_balance
            project.sum_project_cost_balance_base = sum_project_cost_balance_base


    @api.multi
    def _get_total_amounts(self):

        for project in self:
            project.total_paid = 0
            project.total_endowment = 0
            project.total_invoiced = 0
            project.total_base = 0

            domain = [('project_id', '=', project.id), ('state','in',('open', 'paid'))]
            invoices = self.sudo().env['account.invoice'].search(domain)
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

            domain = [('project_id', '=', project.id), ('state', 'in', ('open', 'paid')), ('type', '=', 'out_invoice')]
            last_invoice = self.env['account.invoice'].search(domain, limit=1, order='date_invoice desc')
            if last_invoice:
                project.last_invoice_date = last_invoice.date_invoice

    purchase_invoice_count = fields.Integer ('Purchase Invoices', compute = "_get_purchase_invoice_count", groups="account.group_account_user")
    invoice_count = fields.Integer('Purchase Invoices', compute="_get_invoice_count", groups="account.group_account_user")

    to_invoice = fields.Boolean('Facturable', default=False)
    to_manage = fields.Boolean('Gestionable', default=False)
    last_invoice_date = fields.Date("Ultima factura", compute=_get_last_invoice_date, groups="account.group_account_user")
    invoice_ids = fields.One2many("account.invoice", "project_id", string="Facturas asociadas", groups="account.group_account_user")
    date_DE = fields.Date("Fecha DE")
    date_CITT = fields.Date("Fecha CITT")
    date_resumen = fields.Date("Fecha resumen")
    date_aperture = fields.Date("Fecha apertura")
    register = fields.Char("Registro")
    ci_per_cent = fields.Float("% CI", default="21")


    total_endowment = fields.Float("Importe dotado", digits=dp.get_precision('Account'), compute=_get_total_amounts, groups="account.group_account_user")
    total_invoiced = fields.Float("Importe emitido (con I.V.A.)", digits=dp.get_precision('Account'), compute=_get_total_amounts, groups="account.group_account_user")
    total_paid = fields.Float("Importe pagado (con I.V.A.)", digits=dp.get_precision('Account'), compute=_get_total_amounts, groups="account.group_account_user")
    total_base = fields.Float("Importe emitido (sin I.V.A.)", digits=dp.get_precision('Account'), compute=_get_total_amounts, groups="account.group_account_user")

    apl_state = fields.Many2one("project.aplstate", "Estado administrativo")
    apl_invoice_type = fields.Many2one("project.invoice.type", "Tipo de facturación")
    sum_amount = fields.Float("Total importe total presupuestado", compute =_get_totals)
    sum_total_base = fields.Float("Total base imponible", compute =_get_totals)
    sum_project_invoice_cost = fields.Float("Total coste facturable", compute=_get_totals)
    sum_project_cost_balance = fields.Float("Total presupuestado - facturable", compute=_get_totals)
    sum_project_cost_balance_base = fields.Float("Total imponible - facturable", compute=_get_totals)


    @api.multi
    def show_invoice_purchase(self):

        self.env['res']
        self.ensure_one()
        form_view_ref = self.env.ref('account.invoice_supplier_form', False)
        tree_view_ref = self.env.ref('account.invoice_supplier_tree', False)
        name = _('Supplier Invoices')
        search_view_ref = self.env.ref('account.view_account_invoice_filter', False)
        ctx = dict(self.env.context)
        ctx.update({'project_id': self.id,
                    'default_project_id': self.id,
                    'default_search_project_id': self.id,
                    'default_analytic_account_id': self.analytic_account_id.id,
                    'type': 'in_invoice',
                    })

        return {
            'name': name,
            'domain': [('project_id', '=', self.id), ('type', '=', 'in_invoice')],
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'account.invoice',
            'view_id': tree_view_ref.id,
            'views': [(tree_view_ref and tree_view_ref.id, 'tree'), (form_view_ref and form_view_ref.id, 'form')],
            'type': 'ir.actions.act_window',
            'search_view_id': search_view_ref and search_view_ref.id,
            'context': ctx
        }

    @api.multi
    def show_invoice(self):
        self.ensure_one()
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)
        name = _('Invoices')
        search_view_ref = self.env.ref('account.view_account_invoice_filter', False)
        ctx = dict(self.env.context)
        ctx.update({'project_id': self.id,
                    'default_partner_id': self.partner_id.id,
                    'default_project_id': self.id,
                    'default_search_project_id': self.id,
                    'default_analytic_account_id': self.analytic_account_id.id,
                    'type': 'out_invoice',
                    })

        return {
            'name': name,
            'domain': [('project_id', '=', self.id), ('type', '=', 'out_invoice')],
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'account.invoice',
            'view_id': tree_view_ref.id,
            'views': [(tree_view_ref and tree_view_ref.id, 'tree'), (form_view_ref and form_view_ref.id, 'form')],
            'type': 'ir.actions.act_window',
            'search_view_id': search_view_ref and search_view_ref.id,
            'context': ctx
        }