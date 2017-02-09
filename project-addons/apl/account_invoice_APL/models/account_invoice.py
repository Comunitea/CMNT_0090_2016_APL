# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

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
            self.date_end=False

    project_id = fields.Many2one('project.project', string="Related Project")
    date_end = fields.Datetime('Estimated end date')
    planned_cost = fields.Float('Planned cost')
    account_analytic_id = fields.Many2one(related='project_id.analytic_account_id')
    project_user_id = fields.Many2one(related='project_id.user_id')

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoice, self).default_get(fields)

        return res

    @api.onchange('project_id')
    def onchange_project_id(self):

        self.planned_cost = self.project_id.planned_cost
        self.date_end = self.project_id.date_end
        if self.type in ('out_refund','out_invoice'):
            self.partner_id = self.project_id.partner_id and self.project_id.partner_id or False


class AccountInvoiceLine(models.Model):

    _inherit = 'account.invoice.line'

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoiceLine, self).default_get(fields)
        return res


class ProjectProject(models.Model):

    _inherit ='project.project'

    def _get_purchase_invoice_count(self):
        domain = [('project_id','=',self.id),('type','in',('out_refund','out_invoice'))]
        self.purchase_invoice_count = len(self.env['account.invoice'].search(domain))


    def _get_invoice_count(self):
        domain = [('project_id','=',self.id),('type','in',('in_refund','in_invoice'))]
        self.purchase_invoice_count = len(self.env['account.invoice'].search(domain))


    purchase_invoice_count = fields.Integer ('Purchase Invoices', compute = "_get_purchase_invoice_count", groups='account.group_account_user')
    invoice_count = fields.Integer('Purchase Invoices', compute="_get_invoice_count", groups='account.group_account_user')


    @api.multi
    def show_invoice_purchase(self):
        self.ensure_one()
        form_view_ref = self.env.ref('account.invoice_supplier_form', False)
        tree_view_ref = self.env.ref('account.invoice_supplier_tree', False)
        name = 'Supplier Invoices'
        search_view_ref = self.env.ref('account.view_account_invoice_filter', False)
        ctx = dict(self.env.context)
        ctx.update({'project_id': self.id,
                    'default_partner_id': self.partner_id.id,
                    'default_date_end_estimated': self.date_end,
                    'default_planned_cost': self.planned_cost,
                    'default_project_id': self.id,
                    'default_search_project_id': self.id})

        return {
            'name': name,
            'domain': [('project_id', '=', self.id)],
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
        name = 'Supplier Invoices'
        search_view_ref = self.env.ref('account.view_account_invoice_filter', False)
        ctx = dict(self.env.context)
        ctx.update({'project_id': self.id,
                    'default_partner_id': self.partner_id.id,
                    'default_date_end_estimated': self.date_end,
                    'default_planned_cost': self.planned_cost,
                    'default_project_id': self.id,
                    'default_search_project_id': self.id})

        return {
            'name': name,
            'domain': [('project_id', '=', self.id)],
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'account.invoice',
            'view_id': tree_view_ref.id,
            'views': [(tree_view_ref and tree_view_ref.id, 'tree'), (form_view_ref and form_view_ref.id, 'form')],
            'type': 'ir.actions.act_window',
            'search_view_id': search_view_ref and search_view_ref.id,
            'context': ctx
        }