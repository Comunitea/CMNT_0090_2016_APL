# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp


class ProjectAplType(models.Model):
    _name = "project.type.apl"

    name = fields.Char("Project Type", help="formación, i+d e innovación, análisis sensorial, APF,  institucional,…")

class ProjectAplFinance(models.Model):

    _name="project.finance.apl"


    type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ])
    name = fields.Char("Project Type", help="Europea/internacional, nacional, regional, etc.,…")

class ProjectProject(models.Model):

    _inherit = "project.project"
    _order = 'code ASC'

    @api.multi
    def get_childs_plus(self):
        for project in self:
            child_project_ids_plus = [project.id]
            if project.child_project_ids:
                child_project_ids_plus += [x.id for x in project.child_project_ids]
            project.child_project_ids_plus = [(6, 0, child_project_ids_plus)]

    @api.multi
    def _compute_child_projects_count(self):
        for project in self:
            project.child_project_ids_count = len(project.child_project_ids)

    @api.multi
    def _compute_activity_count(self):
        for project in self:
            project.activity_count = len(project.activity_ids)

    def _get_type_common(self):
        ids = self.env['project.task.type'].search([
            ('case_default', '=', True)])
        return ids


    @api.model
    def refresh_costs(self):

        acts = self.env['project.activity'].search([])
        for activity in acts:
            activity._compute_costs()
        acts = self.env['project.project'].search([])
        for activity in acts:
            activity._compute_costs()

    @api.multi
    def _compute_costs(self):
        for project in self:

            real_cost = 0
            planned_cost = 0
            project_invoice_cost = 0
            tasks = project.task_ids.filtered(lambda x: not x.new_activity_created)
            if tasks:
                default_done = tasks[0].stage_find(tasks[0].project_id.id, [('default_done', '=', True)])
                #default_draft = tasks[0].stage_find(tasks[0].project_id.id, [('default_draft', '=', True)])
                for task in tasks:
                    if default_done == task.stage_id.id:
                        real_cost += task.real_cost
                    #if default_draft == task.stage_id.id:
                    planned_cost += task.planned_cost

            activities = project.activity_ids.filtered(lambda x: not x.parent_task_id)
            for activity in activities:
                project_invoice_cost += activity.budget_price

            project.project_real_cost = real_cost
            project.project_planned_cost = planned_cost
            project.project_invoice_cost = project_invoice_cost
            project.project_cost_balance = project.amount - project_invoice_cost
            project.project_cost_balance_base = project.total_base - project_invoice_cost
            print "[%s] Real: %s, Estimado %s, Invoice cost: %s. "%(project.name, project.project_real_cost, project.project_planned_cost, project.project_invoice_cost)
    @api.multi
    def _compute_child_costs(self):
        for project in self:
            real_cost = 0
            planned_cost = 0
            budget_price = 0
            for sub in project.child_project_ids_plus:
                real_cost += sub.project_real_cost
                planned_cost += sub.project_planned_cost
                budget_price += sub.project_budget_price
            project.real_cost = real_cost
            project.planned_cost = planned_cost
            project.budget_price = budget_price
            project.cost_balance = project.budget_price - project.real_cost



    @api.multi
    def _compute_dead_line(self):
        for project in self:
            domain = [('project_id', '=', project.id), ('date_deadline', '!=', False)]
            project.date_deadline = self.env['project.task']. \
                search(domain, order="date_deadline desc", limit=1).date_deadline

    @api.multi
    def _get_date_end(self):
        for project in self:
            search_domain = [('project_id', '=', project.id), ('date_end', '!=', False)]
            task = self.env['project.task'].search(search_domain, order="date_end desc", limit=1)
            project.date_end = task.date_end if task else False

    @api.multi
    def _get_date_start(self):
        for project in self:
            search_domain = [('project_id', '=', project.id), ('date_start', '!=', False)]
            task = self.env['project.task'].search(search_domain, order="date_start desc", limit=1)
            project.date_start = task.date_start if task else False


    @api.multi
    @api.depends('activity_ids.user_id', 'task_ids.user_id', 'task_ids.user_ids')
    def _get_readable(self):
        for project in self:
            user_ids = project.task_ids.mapped('user_ids').mapped('id') + \
                       project.task_ids.mapped('user_id').mapped('id') + \
                       project.activity_ids.mapped('user_id').mapped('id')
            project.readable = [(6, 0, user_ids)]

    readable = fields.Many2many('res.users', compute="_get_readable", store=True)
    type_ids = fields.Many2many(
        comodel_name='project.task.type', relation='project_task_type_rel',
        column1='project_id', column2='type_id', string='Tasks Stages',
        default=_get_type_common)

    activity_ids = fields.One2many('project.activity', 'project_id', string="Activities")
    activity_count = fields.Integer(compute='_compute_activity_count', string="Activities")

    description = fields.Html(string='Description', default=u'<p><br></p>')
    state = fields.Selection([
        ('template', 'Template'),
        ('draft', 'Draft'),
        ('quoted', 'Presupuestado'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('closed', 'Closed'),
        ('not acepted', 'No aceptado')
    ], required=True, default='draft')
    date_deadline = fields.Date(string='Deadline', compute="_compute_dead_line")
    date_start = fields.Datetime(string='Start Date', compute="_get_date_start")
    date_end = fields.Datetime(string='Ending Date', compute="_get_date_end")
    project_type_apl_id=fields.Many2one("project.type.apl", string="Project type")
    finance_type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ], string="Project finance")
    project_finance_apl_id = fields.Many2one("project.finance.apl", string="Finance type", domain=[('type', '=','finance_type')])
    long_name = fields.Char("Long name")

    planned_cost = fields.Float("Coste previsto", help="Suma de los costes estimados de las tareas",
                                multi=True, compute="_compute_child_costs")
    real_cost = fields.Float("Coste real", help="Suma de costes reales de las tareas",
                             multi=True, compute="_compute_child_costs")
    cost_balance = fields.Float("Balance de costes", help="Coste presupuestado menos coste real",
                                multi=True, compute="_compute_child_costs")
    budget_price = fields.Float("Coste presupuestado", multi=True, compute="_compute_child_costs")

    project_invoice_cost = fields.Float("Coste total facturable", help ="Suma de costes facturables de sus actividades",
                                           multi=True,  compute="_compute_costs")

    project_planned_cost = fields.Float("Coste previsto", help="Suma de los costes estimados de las tareas",
                                multi=True, compute="_compute_costs")
    project_real_cost = fields.Float("Coste real", help="Suma de costes reales de las tareas",
                             multi=True, compute="_compute_costs")
    project_cost_balance = fields.Float("Balance importe total presupuestado", help="Importe total presupuestado - coste facturable",
                                multi=True, compute="_compute_costs")
    project_cost_balance_base = fields.Float("Balance base imponible",
                                        help="Suma de facturas emitidas - coste facturable",
                                        multi=True, compute="_compute_costs")
    project_budget_price = fields.Float("Coste presupuestado")

    color_stage = fields.Integer(string='Color Index', related="stage_id.color")
    stage_id = fields.Many2one('project.task.type', compute="_compute_stage_id", string='Project Stage')
    user_ids = fields.Many2many('res.users', string='Externos Permitidos',
                                index=True, track_visibility='always')
    description = fields.Html(string='Description')

    parent_project_id = fields.Many2one('project.project', string="Project padre")
    child_project_ids = fields.One2many('project.project', 'parent_project_id', string="Sub Proyectos",
                                        help ="Projectos derivados:\n"
                                              "Seguimiento económico está relacionado con el proyecto padre\n"
                                              "Los costes repercuten en el proyecto padre")
    child_project_ids_plus = fields.One2many('project.project', compute="get_childs_plus")
    child_project_ids_count = fields.Integer(compute='_compute_child_projects_count', string="Nº de Sub proyectos")

    amount = fields.Float("Importe total presupuestado", digits=dp.get_precision('Account'))
    accepted_code = fields.Char("Codigo de presupuesto aceptado.", help="Código de presupuesto aceptado")
    partner_contact_id = fields.Many2one('res.partner', "Contacto técnico", domain=[('is_company','=', False), ('type', '=', 'contact')])

    @api.model
    def default_get(self, default_fields):
        ctx = self._context.copy()
        if ctx.get('project_creation_in_progress', False):
            return super(ProjectProject, self).default_get(default_fields)
        default_code = self.env['ir.sequence'].next_by_code('project.project.sequence')
        ctx.update(default_code=default_code)
        return super(ProjectProject, self.with_context(ctx)).default_get(default_fields)

    @api.multi
    @api.depends('task_ids', 'task_ids.stage_id')
    def _compute_stage_id(self):
        for project in self:
            start_stage_id = project.get_first_stage()
            last_stage_id = project.get_last_stage()
            run = False
            project.stage_id = start_stage_id

            for task in project.task_ids:
                if task.stage_id.default_error:
                    project.stage_id = task.stage_id
                    break
                elif task.stage_id.default_running:
                    project.stage_id = task.stage_id
                    run = True
                elif task.stage_id == last_stage_id and not run:
                    project.stage_id = task.stage_id

    def get_first_stage(self):
        domain = [('id', 'in', [v.id for v in self.type_ids])]
        stage1 = self.env['project.task.type'].search(domain, order = 'sequence asc', limit =1)
        return stage1

    def get_draft_stage(self):
        return self.type_ids.filtered(lambda x: x.default_draft)

    def get_done_stage(self):
        return self.type_ids.filtered(lambda x: x.default_done)

    def get_running_stage(self):
        return self.type_ids.filtered(lambda x:x.default_stage)

    def get_last_stage(self):
        domain = [('id', 'in', [v.id for v in self.type_ids])]
        stage1 = self.env['project.task.type'].search(domain, order = 'sequence desc', limit=1)
        return stage1

    def get_date_end(self):
        self._get_date_end(self)

