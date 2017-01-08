# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, tools, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class TaskCosts(models.Model):
    _name="project.task.cost"

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
    quantity= fields.Float("Quantity")
    unit_cost = fields.Float("Unit Cost")
    line_cost = fields.Float("Line Cost", compute="_get_task_line_cost")
    template_cost = fields.Boolean("Template Cost", help="If true, this cost will be copied from template task")

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.unit_cost = self.product_id.standard_price

class ProjectActivity(models.Model):

    _name = "project.activity"

    def _compute_task_cost(self):
        for activity in self:
            if activity.real_cost:
                activity.task_cost = activity.real_cost
            else:
                activity.task_cost = 0
                for task in activity.task_ids:
                    activity.task_cost += task.real_cost or task.amount_cost_ids

    def _compute_planned_task_cost(self):
        for activity in self:
            for task in activity.task_ids:
                activity.planned_cost += task.planned_cost

    def _compute_task_count(self):
        for project in self:
            project.task_count = len(project.task_ids)

    def _compute_dead_line(self):
        for activity in self:
            domain = [('activity_id', '=', activity.id), ('date_deadline', '!=', False)]
            activity.date_deadline = self.env['project.task'].search(domain, order="date_deadline desc", limit = 1).date_deadline

    @api.one
    def _progress_get(self):

        domain= [('activity_id', '=', self.id), ('done', '=', True)]
        tasks = self.env['project.task'].search(domain)
        progress = len(tasks) * 100
        self.progress = progress / (len(self.task_ids) or 1.0)

    @api.depends('task_ids', 'task_ids.stage_id')
    def _compute_stage_id(self):

        for activity in self:
            start_stage_id = activity.project_id.get_first_stage()
            last_stage_id = activity.project_id.get_last_stage()
            run = False
            activity.stage_id = start_stage_id
            for task in activity.task_ids:
                if task.stage_id.default_error:
                    activity.stage_id = task.stage_id
                    break
                elif task.stage_id.default_running:
                    activity.stage_id = task.stage_id
                    run = True
                elif task.stage_id == last_stage_id and not run:
                    activity.stage_id = task.stage_id

    @api.depends('task_ids.stage_id', 'project_id.state')
    def _compute_state(self):
        return
        for activity in self:

            if activity.project_id.state=="closed":
                activity.state="closed"

            elif activity.progress ==1:
                activity.state = "done"


            else:
                activity.state="draft"

                for task in activity.task_ids:
                    if task.stage_id.default_error:
                        activity.state="error"

                        break
                    if task.stage_id.default_running:
                        activity.state="progress"

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, [('fold', '=', False)])

    @api.one
    def _get_date_end(self):

        search_domain = [('activity_id','=',self.id), ('date_end', '!=', False)]
        task = self.env['project.task'].search(search_domain, order="date_end desc", limit = 1)
        self.date_end = task.date_end if task else False

    @api.one
    def _get_date_start(self):

        search_domain = [('activity_id','=',self.id), ('date_start', '!=', False)]
        task = self.env['project.task'].search(search_domain, order="date_start desc", limit = 1)
        self.date_start = task.date_start if task else False

    active = fields.Boolean("Active", default= True)
    name = fields.Char('name', required=True)
    sequence = fields.Integer(string='Sequence', index=True, default=10,
                              help="Gives the sequence order when displaying a list of activities.")
    task_count = fields.Integer(compute='_compute_task_count', string="Tasks count")
    project_id = fields.Many2one('project.project', string='Project')
    task_ids = fields.One2many('project.task', 'activity_id', string="Tasks")#, domain = "[('project_id', '=', project_id)]")
    tag_ids = fields.Many2many('project.tags', string='Tags', oldname='categ_ids')
    date_start = fields.Datetime(string='Start Date', compute="_get_date_start")
    date_end = fields.Datetime(string='Ending Date', compute="_get_date_end")
    user_id = fields.Many2one('res.users',
                              string='Resposable',
                              default=lambda self: self.env.uid,
                              index=True, track_visibility='always')
    color = fields.Integer(string='Color Index', related="stage_id.color")
    progress = fields.Integer(compute='_progress_get', string='Tasks done')
    date_deadline = fields.Date(string='Deadline', compute="_compute_dead_line")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('closed', 'Closed'),
        ('error', 'Error')
    ], compute="_compute_state")
    #stage_id = fields.Many2one("project.task.type", compute="_compute_stage_id", store=True )
    default_error = fields.Boolean(related="stage_id.default_error")
    planned_cost = fields.Float("Planned Cost", help="Planned cost: Sum planned task cost", compute ="_compute_planned_task_cost")
    real_cost = fields.Float("Real Cost", help="Activity Cost")
    task_cost = fields.Float("Task Cost", help = "Task Cost: Sum real task cost",compute="_compute_task_cost")

    use_tasks = fields.Boolean(related="project_id.use_tasks")

    label_tasks = fields.Char(related="project_id.label_tasks")
    alias_id = fields.Many2one(related="project_id.alias_id")

    stage_id = fields.Many2one('project.task.type', string='Stage', track_visibility='onchange', index=True,
                               default=_get_default_stage_id, group_expand='_read_group_stage_ids',
                               domain="[('project_ids', '=', project_id)]", copy=False,
                               compute='_compute_stage_id', store=True)

    description = fields.Html(string='Description')

    @api.multi
    def copy(self, default):

        new_activity = super(ProjectActivity, self).copy(default)
        tasks = self.env['project.task']
        if new_activity.project_id:
            default_stage_id = new_activity.project_id.get_first_stage()

        for task in self.task_ids:
            defaults = {'project_id': new_activity.project_id.id,
                        'activity_id': new_activity.id,
                        'name': task.name,
                        'stage_id': default_stage_id and default_stage_id.id or False}
            new_task = task.copy(defaults)
            tasks += new_task

        new_activity.write({'task_ids': [(6,0,tasks.ids)]})
        return new_activity


    @api.multi
    def map_activity(self, new_project_id):

        activities = self.env['project.activity']
        tasks2 = self.env['project.task']
        new_project = self.browse(new_project_id)
        default_stage_id = False
        min_sequence = 100


        for activity in self:
            if activity.project_id:
                default_stage_id = activity.project_id.get_first_stage()

            default_activity= {
                'name':activity.name,
                'project_id': new_project_id,
                'state': 'draft',
            }
            new_activity = activity.copy(default_activity)
            activities += new_activity

            tasks = self.env['project.task']
            for task in activity.task_ids:
                defaults = {'project_id': new_project_id,
                            'activity_id': new_activity.id,
                            'name': task.name,
                            'stage_id': default_stage_id and default_stage_id.id or False}
                print defaults
                new_task = task.copy(defaults)
                costs = self.env['project.task.cost']
                for cost in task.cost_ids:
                    if cost.template_cost:
                        defaults={'task_id': new_task.id}
                        new_cost = cost.copy(defaults)
                        costs += new_cost

                tasks += new_task
                new_task.write({'cost_ids': [(6,0,costs.ids)]})

            tasks2 += tasks
            #new_project.write({'tasks': [(6, 0, tasks.ids)]})
            new_activity.write({'task_ids': [(6, 0, tasks.ids)]})
            print tasks.ids

        return ({'activity_ids': [(6, 0, activities.ids)],
                           'tasks': [(6, 0, tasks2.ids)]})

    def stage_find(self, section_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        section_ids.extend(self.mapped('project_id').ids)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        return self.env['project.task.type'].search(search_domain, order=order, limit=1).id

class ProjectTask(models.Model):

    _inherit ="project.task"

    def _get_task_costs(self):
        for task in self:
            task.amount_cost_ids=0
            for cost in task.cost_ids:
                task.amount_cost_ids += cost.line_cost

    @api.depends('real_cost', 'amount_cost_ids')
    def _get_real_cost_cal(self):
        for task in self:
            task.real_cost_cal = task.real_cost or task.amount_cost_ids


    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'in Progress'),
        ('done', 'Done'),
        ('closed', 'Closed'),
    ], required=True, default='draft')

    activity_id = fields.Many2one("project.activity", string ="Activity")
    stage_id_color = fields.Integer(related="stage_id.color")
    color = fields.Integer(related="stage_id.color")
    working_color=fields.Integer("Active Color", default=3)
    planned_cost = fields.Float ("Planned Cost", help="Planned cost")
    real_cost = fields.Float("Real Cost", help ="Real cost (after task finish)", copy=False)
    real_cost_cal = fields.Float("Real Cost Cal", help="Real cost or amount_cost_ids", compute='_get_real_cost_cal', store=True)
    cost_ids = fields.One2many("project.task.cost", "task_id", string="Tasks Costs")
    amount_cost_ids = fields.Float("Tasks Costs Amount", compute="_get_task_costs")
    #sobre escribo date_start paraquitar el valor por defecto
    date_start = fields.Datetime(string='Starting Date',
                                 default= '',
                                 index=True, copy=False)
    done = fields.Boolean('Done')
    stage_name = fields.Char(related="stage_id.name")
    #@api.onchange('stage_id')
    #def _onchange_stage_id(self):
    #    self.color=self.stage_id.color
        #

        #if self.stage_id.running_state:
        #    self.color = self.working_color
        #elif self.stage_id.error_state:
        #    self.color = 8project_id.
        #else:
        #    self.state=0

    @api.multi
    def write(self, vals):

        if self.create_uid != self.env.user and self.user_id != self.env.user:
            user_admin = True
        else:
            user_admin = False

        if ('stage_id' in vals):

            if (vals.get('kanban_state', 'normal') == 'blocked' or self.kanban_state == 'blocked'):
                raise UserError(_('You cannot change the state because task is blocked'))

            stage_id =self.env['project.task.type'].browse(vals.get('stage_id'))
            if stage_id.default_running and self.stage_id.name=='draft' and not user_admin:
                raise UserError(_('You cannot change the state (task is in draft state)'))

            if self.stage_id.default_error and not user_admin:
                raise UserError(_('You cannot change the state (task is in error state)'))

            if stage_id.id == self.project_id.get_last_stage().id and not user_admin and False:
                raise UserError(_('You cannot change the state (task is finished)'))

            done = (vals.get('stage_id', False) == self.project_id.get_last_stage().id)
            vals['done'] = done


        result = super(ProjectTask, self).write(vals)

        return result

    @api.onchange('user_id')
    def _onchange_user(self):

        if self.user_id:
            self.date_assign = fields.Datetime.now()

    @api.multi
    def copy(self, default):

        new_task = super(ProjectTask, self).copy(default)
        costs = self.env['project.task.cost']
        for cost in self.cost_ids:
            if cost.template_cost:
                defaults= {'name': cost.name,
                           'product_id': cost.product_id.id,
                           'quantity': cost.quantity,
                           'unit_cost': cost.product_id.standard_price,
                           'task_id': new_task.id}

                new_cost = cost.copy(defaults)
                costs += new_cost
        new_task.write({'cost_ids': [(6, 0, costs.ids)]})
        return new_task

class ProjectAplType(models.Model):
    _name="project.type.apl"

    name=fields.Char("Project Type", help="formación, i+d e innovación, análisis sensorial, APF,  institucional,…")

class ProjectAplFinance(models.Model):

    _name="project.finance.apl"


    type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ])
    name = fields.Char("Project Type", help="Europea/internacional, nacional, regional, etc.,…")



class ProjectProject(models.Model):

    _inherit = "project.project"

    def _compute_activity_count(self):
        for project in self:
            project.activity_count = len(project.activity_ids)

    def _get_type_common(self):
        ids = self.env['project.task.type'].search([
            ('case_default', '=', True)])
        return ids

    def _compute_activity_cost(self):
        for project in self:
            if project.real_cost:
                project.task_cost = project.real_cost
            else:
                for activity in project.activity_ids:
                    project.task_cost += activity.task_cost

    def _compute_planned_activity_cost(self):
        for project in self:
            for activity in project.activity_ids:
                project.planned_cost += activity.planned_cost

    def _compute_dead_line(self):
        for project in self:
            project.date_deadline = False
            for activity in project.activity_ids:
                project.date_deadline = project.date_deadline or max(project.date_deadline, activity.date_deadline)

    @api.model
    def _get_date_end(self):
            search_domain = [('project_id', '=', self.id), ('date_end', '!=', False)]
            task = self.env['project.task'].search(search_domain, order="date_end desc", limit=1)
            self.date_end = task.date_end if task else False

    @api.model
    def _get_date_start(self):

        search_domain = [('project_id', '=', self.id), ('date_start', '!=', False)]
        task = self.env['project.task'].search(search_domain, order="date_start desc", limit=1)
        self.date_start = task.date_start if task else False

    type_ids = fields.Many2many(
        comodel_name='project.task.type', relation='project_task_type_rel',
        column1='project_id', column2='type_id', string='Tasks Stages',
        default=_get_type_common)

    activity_ids = fields.One2many('project.activity', 'project_id', string = "Activities")
    activity_count = fields.Integer(compute='_compute_activity_count', string="Activities")

    planned_cost = fields.Float("Planned Cost", help="Planned cost: Sum planned activity cost",
                                compute="_compute_planned_activity_cost")
    real_cost = fields.Float("Real Cost", help="Project Cost", copy=False)
    task_cost = fields.Float("Task Cost", help="Activities Cost: Sum real activities cost", compute="_compute_activity_cost")
    state = fields.Selection([
        ('template', 'Template'),
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('closed', 'Closed'),
    ], required=True, default='draft')
    date_deadline = fields.Date(string='Deadline', compute="_compute_dead_line")
    date_start = fields.Datetime(string='Start Date', compute="_get_date_start")
    date_end = fields.Datetime(string='Ending Date', compute="_get_date_end")
    project_type_apl_id=fields.Many2one("project.type.apl", string="Tipo de Projecto")
    finance_type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ])
    project_finance_apl_id = fields.Many2one("project.finance.apl", string="Tipo de financiacion", domain=[('type', '=','finance_type')])


    color_stage = fields.Integer(string='Color Index', related="stage_id.color")
    stage_id = fields.Many2one('project.task.type', compute="_compute_stage_id", string='Project Stage')

    @api.depends('activity_ids', 'activity_ids.stage_id')
    def _compute_stage_id(self):

        for project in self:

            start_stage_id = project.get_first_stage()
            last_stage_id = project.get_last_stage()
            run = False
            project.stage_id = start_stage_id
            for activity in project.activity_ids:
                if activity.stage_id.default_error:
                    project.stage_id = activity.stage_id
                    break
                elif activity.stage_id.default_running:
                    project.stage_id = activity.stage_id
                    run = True
                elif activity.stage_id == last_stage_id and not run:
                    project.stage_id = activity.stage_id

    def get_first_stage(self):
        domain = [('id', 'in', [v.id for v in self.type_ids])]
        stage1 = self.env['project.task.type'].search(domain, order = 'sequence asc', limit =1)
        return stage1


    def get_last_stage(self):

        domain = [('id', 'in', [v.id for v in self.type_ids])]
        stage1 = self.env['project.task.type'].search(domain, order = 'sequence desc', limit=1)
        return stage1

    @api.multi
    def map_activities1(self, new_project_id):
        """ copy and map tasks from old to new project """
        activities = self.env['project.activity']
        tasks2 = self.env['project.task']
        new_project = self.browse(new_project_id)
        default_stage_id= False
        min_sequence=100
        default_stage_id = self.get_first_stage()

        for activity in self.activity_ids:


            default_activity= {
                'name':activity.name,
                'project_id': new_project_id,
                'state': 'draft',
            }
            new_activity = activity.copy(default_activity)
            activities += new_activity

            tasks = self.env['project.task']
            for task in activity.task_ids:
                defaults = {'project_id': new_project_id,
                            'activity_id': new_activity.id,
                            'name': task.name,
                            'stage_id': default_stage_id.id}
                print defaults
                new_task = task.copy(defaults)
                costs = self.env['project.task.cost']
                for cost in task.cost_ids:
                    if cost.template_cost:
                        defaults={'task_id': new_task.id}
                        new_cost = cost.copy(defaults)
                        costs += new_cost

                tasks += new_task
                new_task.write({'cost_ids': [(6,0,costs.ids)]})

            tasks2 += tasks
            #new_project.write({'tasks': [(6, 0, tasks.ids)]})
            new_activity.write({'task_ids': [(6, 0, tasks.ids)]})
            print tasks.ids
        new_project.write({'activity_ids': [(6, 0, activities.ids)],
                           'tasks': [(6, 0, tasks2.ids)]}),


        print activities.ids
        return

    @api.multi
    def copy(self, default=None):
        if self.state != "template":
            raise UserError(_('You only copy template project'))


        new_project = super(ProjectProject, self).copy(default)


        new_project.task_ids.unlink()
        new_project.activity_ids.unlink()
        activities = self.env['project.activity']
        tasks = self.env['project_activity']
        for activity in new_project.activity_ids:
            default_activity = {
                'name': activity.name,
                'project_id': new_project.id,
                'state': 'draft',
            }
            new_activity = activity.copy(default_activity)
            activities += new_activity
            tasks += new_activity.task_ids

            new_project.write({'activity_ids': [(6, 0, activities.ids)],
                               'tasks': [(6, 0, tasks.ids)]})

        return new_project

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    case_default = fields.Boolean(
        string='Default for New Projects',
        help='If you check this field, this stage will be proposed by default '
             'on each new project. It will not assign this stage to existing '
             'projects.')

    color = fields.Integer(
        string="Color",
        help="Choose your color"
    )


    default_error = fields.Boolean("Error stage", help="if check, this is an error stage")
    default_running = fields.Boolean("Runnning stage", help="if check, this is an running stage")



class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'





