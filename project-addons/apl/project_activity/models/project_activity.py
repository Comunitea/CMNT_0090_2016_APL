# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp

class TaskCosts(models.Model):

    _name = "project.task.cost"

    def _get_task_line_cost (self):
        for line in self:
            line.line_cost= line.quantity * line.unit_cost

    name = fields.Char('name')
    product_id = fields.Many2one("product.product")
    task_id = fields.Many2one("project.task", copy = False)
    user_id = fields.Many2one('res.users',
                              string='Assigned to',
                              default=lambda self: self.env.uid,
                              index=True, track_visibility='always', copy = False)
    quantity = fields.Float("Quantity")
    unit_cost = fields.Float("Unit Cost")
    line_cost = fields.Float("Line Cost", compute="_get_task_line_cost")
    template_cost = fields.Boolean("Template Cost", help="If true, this cost will be copied from template task")

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.unit_cost = self.product_id.standard_price

class ProjectActivity(models.Model):

    _name = "project.activity"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'code ASC'



    def check_all_cost(self):
        activity_ids = self.env['project.activity'].search([('id','>',0)])
        activity_ids._compute_costs()

    @api.multi
    @api.depends('task_ids.task_real_cost', 'task_ids.task_planned_cost', 'task_ids.stage_id', 'budget_price')
    def _compute_costs(self):

        icp = self.env['ir.config_parameter']
        include_new_activity_created = icp.get_param('project_activity.incluir_solicitudes', '0')

        for activity in self:
            #print (u"Calculando costes de %s"%activity)

            if include_new_activity_created != "0":
                tasks = activity.task_ids
            else:
                tasks = activity.task_ids.filtered(lambda x: not x.new_activity_created)
            real_cost = 0
            planned_cost = 0

            default_done = False
            if tasks:
                default_done = tasks.stage_find(activity.project_id.id, [('default_done', '=', True)])
                default_draft = tasks.stage_find(activity.project_id.id, [('default_draft', '=', True)])
            for task in tasks:
                if default_done == task.stage_id.id:
                    real_cost += task.real_cost
                if default_draft != task.stage_id.id:
                    planned_cost += task.planned_cost

            activity.real_cost = real_cost
            activity.planned_cost = planned_cost
            activity.cost_balance = activity.budget_price - real_cost

            # print "[%s] : Real %s, Estimado %s"%(activity.id, activity.real_cost, activity.planned_cost)

    @api.multi
    def _compute_task_count(self):
        for activity in self:
            activity.task_count = len(activity.task_ids)

    @api.multi
    def _compute_dead_line(self):
        for activity in self:
            domain = [('activity_id', '=', activity.id), ('date_deadline', '!=', False)]
            activity.date_deadline = self.env['project.task'].\
                search(domain, order="date_deadline desc", limit=1).date_deadline

    @api.multi
    def _progress_get(self):
        for activity in self:
            activity.progress = float(len(activity.task_ids.filtered(lambda x: x.stage_id.default_done))) / (len(activity.task_ids) or 1.0) * 100

    @api.one
    def _get_date_end(self):
        for activity in self:
            search_domain = [('activity_id', '=', activity.id), ('date_end', '!=', False)]
            task = self.env['project.task'].search(search_domain, order="date_end desc", limit=1)
            activity.date_end = task.date_end if task else False

    @api.one
    def _get_default_user_id(self):
        self.user_id = self.project_id and self.project_id.user_id or self.env.user

    @api.multi
    def _get_date_start(self):
        for activity in self:
            search_domain = [('activity_id', '=', activity.id), ('date_start', '!=', False)]
            task = self.env['project.task'].search(search_domain, order="date_start asc", limit=1)
            activity.date_start = task.date_start if task else False


    @api.multi
    @api.depends('project_id', 'code')
    def _get_long_code(self):
        for activity in self:
            if activity.project_id:
                activity.long_code = "%s-%s"%(activity.project_id.code, activity.code)
            else:
                activity.long_code = activity.code

    active = fields.Boolean("Active", default= True)
    name = fields.Char('name', required=True)
    sequence = fields.Integer(string='Sequence', index=True, default=1,
                              help="Gives the sequence order when displaying a list of activities.")
    task_count = fields.Integer(compute='_compute_task_count', string="Tasks count")
    project_id = fields.Many2one('project.project', string='Project', copy=True, required=True)
    task_ids = fields.One2many('project.task', 'activity_id', string="Tasks", copy = False)#, domain = "[('project_id', '=', project_id)]")
    tag_ids = fields.Many2many('project.tags', string='Tags', oldname='categ_ids')
    date_start = fields.Datetime(string='Start Date', compute="_get_date_start")
    date_end = fields.Datetime(string='Ending Date', compute="_get_date_end")

    # user_id = fields.Many2one('res.users',
    #                           string='Manager',
    #                           default=_get_default_user_id,
    #                           index=True, track_visibility='always')
    user_id = fields.Many2one('res.users', string='Assigned to',default = _get_default_user_id,
                              index=True, track_visibility='always', required=True)

    progress = fields.Integer(compute='_progress_get', string='Tasks done')
    date_deadline = fields.Date(string='Deadline', compute="_compute_dead_line")

    planned_cost = fields.Float("Coste previsto", multi=True, help="Suma de los costes estimados de las tareas", compute ="_compute_costs", store=True, compute_sudo=True)
    real_cost = fields.Float("Coste real", multi=True, help="Suma de costes reales de las tareas", compute="_compute_costs", store=True, compute_sudo=True)
    budget_price = fields.Float("Coste facturable")

    cost_balance = fields.Float("Balance de costes", help="Coste presupuestado menos coste real",
                                compute="_compute_costs", multi=True, store=True, compute_sudo=True)
    use_tasks = fields.Boolean(related="project_id.use_tasks")
    code = fields.Char("Code", copy=False)
    long_code = fields.Char("Complete Id", compute="_get_long_code", store=True)
    label_tasks = fields.Char(related="project_id.label_tasks")
    alias_id = fields.Many2one(related="project_id.alias_id")
    description = fields.Html(string='Notas del proyecto')
    parent_task_id = fields.Many2one('project.task', string="Parent task",
                                     help="This activity was created from this task")
    accepted_code = fields.Char("Código de facturación", help="Código de facturación")

    @api.model
    def default_get(self, default_fields):

        default_user_id=False
        if self.env.context.get('default_project_id', False):
            default_project_id = self.env.context.get('default_project_id', False)
            default_user_id = self.env['project.project'].browse(default_project_id).user_id.id or self.env.uid

        default_code = self.env['ir.sequence'].next_by_code('project.activity.sequence')
        contextual_self = self.with_context(default_code=default_code, default_user_id=default_user_id)
        return super(ProjectActivity, contextual_self).default_get(default_fields)

    @api.multi
    def copy(self, default):
        new_activity = super(ProjectActivity, self).copy(default)
        return new_activity
        # self.ensure_one()
        # new_activity = super(ProjectActivity, self).copy(default)
        # tasks = []
        # project_id = default.get('project_id', False) or self.project_id.id or False
        # for task in self.task_ids:
        #     defaults = {
        #                 'activity_id': new_activity.id,
        #                 'name': task.name,
        #                 'date_start': fields.Datetime.now(),
        #                 'date_end': fields.Datetime.from_string(fields.Datetime.now()) + timedelta(
        #                     minutes=(task.planned_hours - int(task.planned_hours)) * 60) +
        #                             timedelta(hours=int(task.planned_hours)),
        #                 'project_id': project_id}
        #     new_task = task.copy(defaults)
        #     tasks += new_task
        #
        # new_activity.write({'task_ids': [(6,0,[x.id for x in tasks])]})
        # return new_activity

    @api.multi
    def write(self, vals):
        for activity in self:
            if vals.get('project_id', False):
                activity.task_ids.project_id = vals['project_id']
        res = super(ProjectActivity, self).write(vals)
        return res

    @api.multi
    def unlink(self):
        for activity in self:
            for task in activity.task_ids:
                task.unlink()
        return super(ProjectActivity, self).unlink()

    @api.model
    def create(self, vals):

        if not 'code' in vals:
            vals['code'] = self.env['ir.sequence'].next_by_code('project.activity.sequence')
        return super(ProjectActivity, self).create(vals)
