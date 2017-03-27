# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import datetime, timedelta
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
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'code ASC'

    @api.multi
    @api.depends('task_ids.real_cost')
    def _compute_task_cost(self):
        for activity in self:
            if activity.real_cost:
                activity.task_cost = activity.real_cost
            else:
                activity.task_cost = 0
                for task in activity.task_ids:
                    if task.new_activity_created:
                        activity.task_cost += task.new_activity_created.task_cost
                    else:
                        activity.task_cost += task.real_cost

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

        contador = 0
        for task in self.task_ids:
            if task.stage_id.default_done:
                contador += 1

        progress = contador * 100
        self.progress = progress / (len(self.task_ids) or 1.0)

    @api.depends('task_ids', 'task_ids.stage_id', 'project_id')
    def _compute_stage_id(self):
        return

        for activity in self:
            if activity.project_id:
                done =0
                draft=0

                activity.stage_id = activity.project_id.get_draft_stage()
                for task in activity.task_ids:

                    if task.stage_id.default_done:
                        done=+1
                    elif task.stage_id.default_draft:
                        draft += 1

                if done == len(activity.task_ids):
                    pass


            else:
                activity.stage_id = False


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
        stage_id = self.stage_find(project_id, [('fold', '=', False)])
        return stage_id

    @api.one
    def _get_date_end(self):

        search_domain = [('activity_id','=',self.id), ('date_end', '!=', False)]
        task = self.env['project.task'].search(search_domain, order="date_end desc", limit = 1)
        self.date_end = task.date_end if task else False

    @api.one
    def _get_default_user_id(self):

        self.user_id = self.project_id and self.project_id.user_id or self.env.user

    @api.one
    def _get_date_start(self):

        search_domain = [('activity_id','=',self.id), ('date_start', '!=', False)]
        task = self.env['project.task'].search(search_domain, order="date_start asc", limit = 1)
        self.date_start = task.date_start if task else False

    @api.one
    def _get_long_code(self):
        try:
            if self.project_id:
                self.long_code = "%s-%s"%(self.project_id.code , self.code)
                return
        except:
            pass
        self.long_code = self.code

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
    budget_price = fields.Float("Importe presupuestado")
    use_tasks = fields.Boolean(related="project_id.use_tasks")
    code = fields.Char("Code", copy=False)
    long_code = fields.Char("Complete Id", compute="_get_long_code")
    label_tasks = fields.Char(related="project_id.label_tasks")
    alias_id = fields.Many2one(related="project_id.alias_id")

    stage_id = fields.Many2one('project.task.type', string='Stage', track_visibility='onchange', index=True,
                               default=_get_default_stage_id, group_expand='_read_group_stage_ids',
                               domain="[('project_ids', '=', project_id)]", copy=False,
                               compute='_compute_stage_id', store=True)

    description = fields.Html(string='Description')
    master_activity_id = fields.Many2one('project.activity', string="Template Activity", domain=[('is_template', '=', True)], copy= False)
    is_template = fields.Boolean('Template activity', copy=True)
    parent_task_id = fields.Many2one('project.task', string="Parent task",
                                     help="This activity was created from this task")


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
    def compute_task_cost(self):
        self._compute_task_cost()


    @api.onchange('master_activity_id')
    def onchange_master_activity_id(self):
        if not self.master_activity_id:
            return

        #buscamos el default_stage para el projecto
        domain=[('project_id','=', self.project_id), ('default_draft', '=', True)]
        default_stage = self.env['project.task.type'].search(domain, limit =1)



        tasks = self.env['project.task']

        for task in self.master_activity_id.task_ids:
            defaults = {'project_id': self.project_id.id,
                        'activity_id': self.id,
                        'name': task.name,
                        'stage_id': default_stage and default_stage.id or False}

            new_task = task.copy(defaults)
            costs = self.env['project.task.cost']
            for cost in task.cost_ids:
                if cost.template_cost:
                    defaults = {'task_id': new_task.id}
                    new_cost = cost.copy(defaults)
                    costs += new_cost

            tasks += new_task
            new_task.write({'cost_ids': [(6, 0, costs.ids)]})
        # new_project.write({'tasks': [(6, 0, tasks.ids)]})
        vals = {'stage_id': default_stage.id,
                'project_id': self.project_id.id,
                'name': self.master_activity_id.name,
                'tag_ids': [(6, 0, self.master_activity_id.tag_ids)],
                'task_ids': [(6, 0, tasks.ids)]}

        self.write(vals)

        return self

    @api.multi
    def copy(self, default):
        self.ensure_one()
        new_activity = super(ProjectActivity, self).copy(default)
        tasks = []
        project_id = default.get('project_id', False) or self.project_id.id or False
        for task in self.task_ids:
            defaults = {
                        'activity_id': new_activity.id,
                        'name': task.name,
                        'date_start': fields.Datetime.now(),
                        'date_end': fields.Datetime.from_string(fields.Datetime.now()) + timedelta(
                            minutes=(task.planned_hours - int(task.planned_hours)) * 60) +
                                    timedelta(hours=int(task.planned_hours)),
                        'project_id': project_id}
            new_task = task.copy(defaults)
            #new_task.name = "%s.%s"%(task.name, new_task.code.split('.')[1])
            tasks += new_task

        new_activity.write({'task_ids': [(6,0,[x.id for x in tasks])]})
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
            new_activity.write({'task_ids': [(6, 0, tasks2.ids)]})


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

    @api.multi
    def write(self, vals):

        for activity in self:
            if 'stage_id' and activity.parent_task_id and False:
                activity.parent_task_id.write({'date_start': fields.Datetime.now(),
                                               'date_end': fields.Datetime.now(),
                                               'stage_id': activity.project_id.get_draft_stage()})


            if vals.get('project_id') and vals['project_id'] != activity.project_id.id:
                stage_id = self.env['project.project'].browse(vals['project_id']).get_draft_stage()
                activity.task_ids.write({'project_id': vals['project_id'],})

        res = super(ProjectActivity, self).write(vals)
        return res

    @api.multi
    def unlink(self):
        for activity in self:
            for task in activity.task_ids:
                task.unlink()

        return super(ProjectActivity, self).unlink()

class ProjectTask(models.Model):

    _inherit ="project.task"
    _order = 'date_start ASC'

    def _get_task_costs(self):
        for task in self:
            task.amount_cost_ids=0
            for cost in task.cost_ids:
                task.amount_cost_ids += cost.line_cost

    @api.multi
    @api.depends('real_cost', 'amount_cost_ids')
    def _get_real_cost_cal(self):
        for task in self:
            task.real_cost_cal = task.real_cost or task.amount_cost_ids

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        #TODO Sobre escribo para
        project_id = self.env.context.get('default_project_id')
        res = self.stage_find(project_id, [('fold', '=', False)])
        stage = self.env['project.task.type'].browse(res).default_draft
        if not stage:
            res = self.env['project.task.type'].search([('default_draft','=',True)], order = 'sequence,id ASC', limit = 1).id
        return res

    @api.multi
    @api.depends('stage_id')
    def _get_task_state(self):

        for task in self:
            if task.stage_id.default_draft:
                task.state="draft"
            if task.stage_id.default_error:
                task.state="error"
            if task.stage_id.default_done:
                task.state="done"
            if task.stage_id.default_running:
                task.state="progress"

    @api.one
    def _get_long_code(self):
        try:
            if self.activity_id:
                self.long_code = "%s-%s" % (self.activity_id.long_code, self.code)
                return
        except:
            pass
        self.long_code = self.code


    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'Progress'),
        ('done', 'Done'),
        ('no schedule', 'No schedule'),
        ('error', 'Error'),
    ], compute = "_get_task_state", store=True)

    activity_id = fields.Many2one("project.activity", string ="Activity", domain=[('project_id', '=', 'project_id.id')])
    color = fields.Integer(related="stage_id.color")
    planned_cost = fields.Float ("Planned Cost", help="Planned cost", required=True)
    real_cost = fields.Float("Real Cost", help ="Real cost (after task finish)")
    real_cost_cal = fields.Float("Real Cost Cal", help="Real cost or amount_cost_ids",
                                 compute='_get_real_cost_cal')
    cost_ids = fields.One2many("project.task.cost", "task_id", string="Tasks Costs")
    amount_cost_ids = fields.Float("Tasks Costs Amount", compute="_get_task_costs")
    #sobre escribo date_start para poner el valor por defecto y required = True
    date_start = fields.Datetime(string='Starting Date',
                                 default=fields.Datetime.now,
                                 index=True, copy=False, required = True)
    date_end = fields.Datetime(string='Ending Date', index=True,
                               default=fields.Datetime.now,
                               copy=False,required = True)
    code = fields.Char("Code", copy=False)
    long_code = fields.Char("Complete Id", compute="_get_long_code")
    no_schedule = fields.Boolean("No schedule", help='if check, task manager will created a new activity from this task', default = False)
    new_activity_id = fields.Many2one("project.activity", string="Activity template", help ="New activity will be created from this task when done",
                                      domain =[('is_template','=', True)])
    new_activity_created = fields.Many2one("project.activity", string="Related activity", help ="New activity created from this task")
    is_template = fields.Boolean(related='activity_id.is_template')
    user_id = fields.Many2one('res.users', string='Responsable',
                              index=True, track_visibility='always')
    default_draft = fields.Boolean(related='stage_id.default_draft')
    default_done = fields.Boolean(related='stage_id.default_done')
    ok_calendar = fields.Boolean("Ok Calendar", default=True)
    date_st_day = fields.Date(string="Dia de la tarea")

    @api.onchange('project_id')
    def _onchange_project(self):
        x = super(ProjectTask,self)._onchange_project()

        if self.project_id:
            x = {'domain': {'activity_id': [('project_id', '=', self.project_id.id)]},
                 }
            if self.activity_id.project_id.id != self.project_id.id:
                self.activity_id = False
        return x

    @api.constrains('planned_cost')
    def _check_costs(self):

        if self.planned_cost <= 0.00:
            raise ValidationError(_('Error! Check planned cost'))

    @api.onchange('planned_hours')
    def _onchange_planned_hours(self):

        start_dt = fields.Datetime.from_string(self.date_start)
        end_dt = start_dt + timedelta(minutes=(self.planned_hours - int(self.planned_hours)) * 60) + timedelta(
            hours=int(self.planned_hours))
        self.date_end = end_dt

    @api.onchange('planned_cost')
    def _onchange_planned_cost(self):
        if self.real_cost == 0.00 and not self.new_activity_created:
            self.real_cost = self.planned_cost


    @api.onchange('date_start')
    def _onchange_dates(self):
        self._onchange_planned_hours()
        return

    @api.model
    def default_get(self, default_fields):

        contextual_self = self.with_context()
        if not 'default_project_id' in self._context and 'default_activity_id' in self._context:
            py = self.env['project.activity'].browse(self._context['default_activity_id'])
            default_project_id = py and py.project_id and py.project_id.id or False
            contextual_self = contextual_self.with_context(default_project_id=default_project_id)

        if self._context.get('default_activity_id', False):
            default_activity_id = self.env.context.get('default_activity_id', False)
            default_user_id = self.env['project.activity'].browse(default_activity_id).user_id.id or self.env.uid
            contextual_self = contextual_self.with_context(default_user_id=default_user_id)

        default_code = self.env['ir.sequence'].next_by_code('project.task.sequence')
        contextual_self = contextual_self.with_context(default_code=default_code)
        res = super(ProjectTask, contextual_self).default_get(default_fields)
        return res

    @api.multi
    def write(self, vals):


        if self.user_id.id != self.env.user.id and self.env.user.id != 1:
            if 'date_start' in vals or \
                            'date_end' in vals:
                raise ValidationError ("No tienes permiso para hacer esto")


        vals['date_st_day']=vals.get('date_start', False)


        for task in self:
            if vals.get('project_id'):
                stage_id = self.env['project.project'].browse(vals.get('project_id')).get_draft_stage()
                vals['stage_id']=stage_id

        result = super(ProjectTask, self).write(vals)

        return result

    @api.multi
    def copy(self, default):

        new_task = super(ProjectTask, self).copy(default)
        return new_task

        # costs = self.env['project.task.cost']
        # for task in self:
        #     new_task = super(ProjectTask, task).copy(default)
        #
        #     for cost in task.cost_ids:
        #         if cost.template_cost:
        #             defaults = {'name': cost.name,
        #                         'product_id': cost.product_id.id,
        #                         'quantity': cost.quantity,
        #                         'unit_cost': cost.product_id.standard_price,
        #                         'task_id': new_task.id,
        #                         }
        #             new_cost = cost.copy(defaults)
        #             costs += new_cost
        #     new_task.write({'cost_ids': [(6, 0, costs.ids)]})
        #     return new_task

    def new_activity_from_task(self):

        if not self.project_id:
            raise UserError(_('You need set "project_id"'))

        if self.env.user not in self.user_ids:
            raise UserError(_('Not asigned user'))

        if not self.new_activity_id:
            if len(self.user_ids)>1:
                raise UserError(_('More than one assigned user'))
            default = {
                'project_id': self.project_id.id,
                'is_template': False,
                'user_id': self.user_ids and self.user_ids[0].id or self.user_id.id,
                'name': "%s/%s/%s"%(self.project_id.code, self.activity_id.code, self.code),
                'parent_task_id': self.id


                }
            new_activity = self.sudo().new_activity_id.create(default)
            #self.sudo.new_activity_created = new_activity
            #self.sudo.new_activity_id = False

            self.sudo().write({'new_activity_created': new_activity.id,
                             'new_activity_id':False})
            #self.stage_id = self.project_id.get_done_stage()

            return {'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'project.activity',
                    'res_id': new_activity.id,
                    }
        if self.new_activity_id:
            raise UserError(_('Template activities not implemented'))

        if not self.new_activity_id.is_template:
            raise UserError(_('"New activity from task" must be template activity'))
        if not self.project_id:
            raise UserError(_('You need set "project_id"'))
        self = self.with_context(show_template=True)

        default={
            'project_id': self.project_id.id,
            'is_template': False
        }

        new_activity = self.new_activity_id.copy(default)
        tasks = []
        vals = {
                'no_schedule': False,
                'project_id': self.project_id.id
        }
        new_activity.task_ids.write(vals)

        self.new_activity_created = new_activity
        self.new_activity_id = False
        self.stage_id = self.project_id.get_done_stage()

        return True

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
    _order = 'code ASC'

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
                    for task in activity.task_ids:
                        project.task_cost += task.real_cost


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
    project_type_apl_id=fields.Many2one("project.type.apl", string="Project type")
    finance_type = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
    ], string="Project finance")
    project_finance_apl_id = fields.Many2one("project.finance.apl", string="Finance type", domain=[('type', '=','finance_type')])
    long_name = fields.Char("Long name")

    color_stage = fields.Integer(string='Color Index', related="stage_id.color")
    stage_id = fields.Many2one('project.task.type', compute="_compute_stage_id", string='Project Stage')
    user_ids = fields.Many2one("res.users", "Usuarios Restringidos")



    @api.model
    def default_get(self, default_fields):
        default_code = self.env['ir.sequence'].next_by_code('project.project.sequence')
        contextual_self = self.with_context(default_code=default_code)
        return super(ProjectProject, contextual_self).default_get(default_fields)

    @api.onchange('user_id')
    def _onchange(self):
        for task in self.task_ids:
            task.user_id =self.user_id


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

    def get_draft_stage(self):
        for stage in self.type_ids:
            if stage.default_draft:
                return stage.id

    def get_done_stage(self):
        for stage in self.type_ids:
            if stage.default_done:
                return stage.id

    def get_running_stage(self):
        for stage in self.type_ids:
            if stage.default_running:
                return stage.id

    def get_last_stage(self):

        domain = [('id', 'in', [v.id for v in self.type_ids])]
        stage1 = self.env['project.task.type'].search(domain, order = 'sequence desc', limit=1)
        return stage1

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

    def get_date_end(self):
        self._get_date_end(self)


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
    default_draft = fields.Boolean("Draft stage", help="if check, this is a draft stage")
    default_done = fields.Boolean("Done stage", help="if check, this is an done stage")

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'





