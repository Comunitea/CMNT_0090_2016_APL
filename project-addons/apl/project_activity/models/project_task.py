# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp

from odoo.tools import html_sanitize
import threading
import logging
_logger = logging.getLogger(__name__)

class MailMail(models.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _inherit = 'mail.mail'

    @api.model
    def process_email_queue(self, ids=None):
        """Send immediately queued messages, committing after each
           message is sent - this is not transactional and should
           not be called during another transaction!

           :param list ids: optional list of emails ids to send. If passed
                            no search is performed, and these ids are used
                            instead.
           :param dict context: if a 'filters' key is present in context,
                                this value will be used as an additional
                                filter to further restrict the outgoing
                                messages to send (by default all 'outgoing'
                                messages are sent).
        """
        if not self.ids:
            filters = ['&',
                       ('state', '=', 'outgoing'),
                       '|',
                       ('scheduled_date', '<', datetime.now()),
                       ('scheduled_date', '=', False)]

            if 'filters' in self._context:
                filters.extend(self._context['filters'])
            ids = self.search(filters).ids
        res = None
        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            for id in ids:
                mesg = self.browse(id)
                print(u"Enviando {} con autocommit {}".format(mesg.id, auto_commit))
                res = mesg.send(auto_commit=auto_commit)
                print(u"Envio OK")
        except Exception:
            _logger.exception("Failed processing mail queue")
        return res

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


class ProjectTask(models.Model):

    _inherit ="project.task"
    _order = 'date_start ASC'

    def _get_task_costs(self):
        for task in self:
            task.amount_cost_ids=0
            for cost in task.cost_ids:
                task.amount_cost_ids += cost.line_cost

    @api.multi
    def _get_costs(self):
        for task in self:
            if task.new_activity_created:
                task.planned_cost = task.new_activity_planned_cost
                task.real_cost = task.new_activity_real_cost
            else:
                task.planned_cost = task.task_planned_cost
                task.real_cost = task.task_real_cost

    @api.multi
    @api.depends('real_cost', 'amount_cost_ids')
    def _get_real_cost_cal(self):
        for task in self:
            task.real_cost_cal = task.real_cost or task.amount_cost_ids


    def _get_draft_stage_id(self):
        """ Gives default stage_id """
        #TODO Sobre escribo para
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, [('default_draft', '=', True)])

    @api.multi
    @api.depends('stage_id')
    def _get_task_state(self):

        for task in self:
            if task.stage_id.default_draft:
                task.state = "draft"
            elif task.stage_id.default_error:
                task.state = "error"
            elif task.stage_id.default_done:
                task.state = "done"
            elif task.stage_id.default_running:
                task.state = "progress"
            else:
                task.state = "error"
            #task.message_post("Ha ocurrido un error al recuperar el estado de la tarea")

    @api.multi
    @api.depends('activity_id', 'code')
    def _get_long_code(self):
        for task in self:
            if task.activity_id:
                task.long_code = "%s-%s"%(task.activity_id.long_code, task.code)
            else:
                task.long_code = task.code

    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'Progress'),
        ('done', 'Done'),
        ('no schedule', 'No schedule'),
        ('error', 'Error'),
    ], compute = "_get_task_state", store=True)

    activity_id = fields.Many2one("project.activity", string="Activity", domain=[('project_id', '=', 'project_id.id')])
    color = fields.Integer(related="stage_id.color")

    planned_cost = fields.Float ("Coste previsto", help="Coste previsto inicialmente de la tarea",
                                 compute=_get_costs, multi=True,
                                 )
    real_cost = fields.Float("Coste real", help="Coste real de la tarea.\nDebería ser confirmado una vez finalizada",
                             compute=_get_costs, multi=True,
                             )

    new_activity_planned_cost = fields.Float(related="new_activity_created.planned_cost", string="Coste previsto",
                                             help="Coste previsto inicialmente de la tarea. Heredado de la actividad asociada")
    new_activity_real_cost = fields.Float(related="new_activity_created.real_cost", string="Coste real", help="Coste real de la tarea.\nHeredado de la actividad asociada")
    task_planned_cost = fields.Float("Coste previsto", help="Coste previsto inicialmente de la tarea", required=True)
    task_real_cost = fields.Float("Coste real", help="Coste real de la tarea.\nDebería ser confirmado una vez finalizada")
    real_cost_cal = fields.Float("Real Cost Cal", help="Real cost or amount_cost_ids",
                                 compute='_get_real_cost_cal')

    cost_ids = fields.One2many("project.task.cost", "task_id", string="Tasks Costs")
    amount_cost_ids = fields.Float("Tasks Costs Amount", compute="_get_task_costs")

    date_start = fields.Datetime(string='Starting Date',
                                 index=True, copy=False, required=True)
    date_end = fields.Datetime(string='Ending Date', index=True,
                               copy=False,required=True)
    code = fields.Char("Code", copy=False)
    long_code = fields.Char("Complete Id", compute="_get_long_code", store=True)
    no_schedule = fields.Boolean("No schedule", help='if check, task manager will created a new activity from this task', default = False)
    new_activity_id = fields.Many2one("project.activity", string="Activity template", help ="New activity will be created from this task when done")

    new_activity_created = fields.Many2one("project.activity", string="Related activity", help ="New activity created from this task")
    user_id = fields.Many2one('res.users', string='Responsable',
                              index=True, track_visibility='always')
    default_draft = fields.Boolean(related='stage_id.default_draft')
    default_done = fields.Boolean(related='stage_id.default_done')
    default_running = fields.Boolean(related='stage_id.default_running')
    ok_calendar = fields.Boolean("Ok Calendar", default=True)

    #date_st_day = fields.Date(string="Dia de la tarea")
    stage_id = fields.Many2one('project.task.type', string='Stage', track_visibility='onchange', index=True,
                               default=_get_draft_stage_id, group_expand='_read_group_stage_ids',
                               domain="[('project_ids', '=', project_id)]", copy=False)

    user_ids = fields.Many2many('res.users', string='Asignada a',
                                index=True, track_visibility='always', required=True)
    equipment_id = fields.Many2one("maintenance.equipment", 'Equipment')

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        if not isinstance(self.id, int):
            if self.project_id:
                self.stage_id = self.stage_find(self.project_id.id, [('default_draft', '=', True)])
            else:
                self.stage_id = False

    @api.onchange('activity_id')
    def onchange_activity_id(self):
        if self.activity_id:
            if self.activity_id.project_id != self.project_id:
                self.project_id = self.activity_id.project_id


    @api.onchange('project_id')
    def _onchange_project(self):
        x = super(ProjectTask,self)._onchange_project()

        if self.activity_id.project_id != self.project_id:
            self.activity_id = False

        if self.project_id and self.project_id not in self.stage_id.project_ids:
            self.stage_id = self.stage_find(self.project_id.id, [('default_draft', '=', True)])
            x = {'domain': {'activity_id': [('project_id', '=', self.project_id.id)]},}

        return x


    @api.constrains('task_planned_cost')
    def _check_costs(self):
        if self.task_planned_cost <= 0.00 and not self.new_activity_created:
            raise ValidationError(_('Error! Check planned cost'))

    @api.onchange('task_planned_cost')
    def _onchange_planned_cost(self):
        if self.task_real_cost == 0.00:
            self.task_real_cost = self.task_planned_cost

    @api.onchange('date_start', 'planned_hours', 'date_end')
    def on_change_task_times(self):
        onchange_field = self._context.get('onchange_field', False)

        if onchange_field != 'date_end' and not self._context.get('calendar_view', False):
            start_dt = fields.Datetime.from_string(self.date_start)
            end_dt = start_dt + timedelta(minutes=(self.planned_hours - int(self.planned_hours)) * 60) + timedelta(
                hours=int(self.planned_hours))
            self.date_end = end_dt
        else:
            date_end = fields.Datetime.from_string(self.date_end)
            ph = date_end - fields.Datetime.from_string(self.date_start)
            self.planned_hours = ph.seconds / 3600.00

    @api.multi
    def write(self, vals):
        if len(self) == 1 and html_sanitize(vals.get('description', False)) == self.description and False:
            vals.pop('description')
            if not vals:
                return True
        if self._context.get('calendar_view', False) and 'date_end' in vals and 'date_start' in vals:
            date_end = fields.Datetime.from_string(vals.get('date_end'))
            ph = date_end - fields.Datetime.from_string(vals.get('date_start'))
            vals['planned_hours'] = ph.seconds / 3600.00
        res = super(ProjectTask, self).write(vals)
        if res:
            new_self = self.sudo()
            activity_ids = new_self.mapped('activity_id') + new_self.mapped('new_activity_created') + new_self.mapped('activity_id').mapped('parent_task_id').mapped('activity_id')
            activity_ids._compute_costs()

        return res


    @api.model
    def default_get(self, default_fields):

        ctx = self._context.copy()

        if not 'default_project_id' in ctx and 'default_activity_id' in ctx:
            py = self.env['project.activity'].browse(self._context['default_activity_id'])
            default_project_id = py and py.project_id and py.project_id.id or False
            ctx.update(default_project_id=default_project_id)

        if self._context.get('default_activity_id', False):
            default_activity_id = self.env.context.get('default_activity_id', False)
            default_user_id = self.env['project.activity'].browse(default_activity_id).user_id.id or self.env.uid
            ctx.update(default_user_id=default_user_id)

        if ctx.get('calendar_view', False):
            ctx.update(default_user_id=ctx.get('uid', False))

        default_code = self.env['ir.sequence'].next_by_code('project.task.sequence')
        ctx.update(default_code=default_code)

        if not ctx.get('default_date_end', False):
            ctx.update(default_date_end=fields.Datetime.now())
        if not ctx.get('default_date_start', False):
            ctx.update(default_date_start=fields.Datetime.now())

        res = super(ProjectTask, self.with_context(ctx)).default_get(default_fields)

        return res

    @api.onchange('user_id')
    def _onchange_user(self):
        return

    @api.multi
    def copy(self, default):

        new_task = super(ProjectTask, self).copy(default)
        return new_task

    def new_activity_from_task(self):

        if not self.project_id:
            raise UserError('Necesitas indicar un projecto')

        if self.env.user != self.user_id and \
                        self.env.user not in self.user_ids and \
                        self.env.user.id != 1:
            raise UserError('No tienes permisos para esto. '
                            'No eres responsable ni estás asignado')
        if len(self.user_ids) > 1:
            raise UserError('Solo puedes asignar un usuario')

        if self.new_activity_created:
            raise UserError(_("Ya has creado una actividad desde esta tarea: %s")%self.new_activity_created.name)

        if not self.new_activity_created:
            default = {
                'project_id': self.project_id.id,
                'user_id': self.user_ids and self.user_ids[0].id or self.user_id.id,
                'name': "%s/%s/%s"%(self.project_id.code, self.activity_id.code, self.code),
                'parent_task_id': self.id
                }
            new_activity = self.sudo().new_activity_id.create(default)
            done_stage = self.project_id.get_done_stage()
            self.sudo().write({'new_activity_created': new_activity.id,
                               'new_activity_id': False,
                               'stage_id': done_stage and done_stage.id})

            return {'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'project.activity',
                    'res_id': new_activity.id,
                    }

        return True

    def set_as_done(self):
        allowed_users = self.get_users()
        if self.env.user in allowed_users:
            ctx = self._context.copy()
            ctx.update({'tracking_disable': True})
            self.sudo().with_context(ctx).write({'stage_id': self.stage_find(self.project_id.id, [('default_done','=', True)])})
            self.sudo().write({'date_end': fields.Datetime.now()})

            body = _('%s ha marcado la tarea como finalizada.') % (self.env.user.name)
            # TODO change SUPERUSER_ID into user.id but catch errors
            return self.message_post(body=body)


    def get_users(self):
        users = []
        for user in self.user_ids:
            users.append(user)
        users.append(self.project_id.user_id)
        users.append(self.activity_id.user_id)
        users = list(set(users))
        return users

