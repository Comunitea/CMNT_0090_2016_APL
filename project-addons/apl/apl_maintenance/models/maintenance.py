# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.fields import Datetime
import pytz

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.multi
    def write(self, vals):
        #todo hay un cron que crea maintenance_request el dia que hay
        #esta programdo en la ficha del equipo pero entonces no aparecen en la agenda

        res = super(MaintenanceRequest, self).write(vals)
        if vals.get('stage_id', False) and self.maintenance_type=='preventive':
            stage_id = self.env['maintenance.stage'].browse(vals.get('stage_id', False))
            if stage_id.done == True:
                #creamos uno nuevo
                schedule_date = fields.Datetime.from_string(self.close_date) + timedelta(days = self.equipment_id.period)
                request_date = self.close_date
                maintenance_type ='preventive'
                vals = {
                    'request_date': schedule_date,
                    'schedule_date': schedule_date,
                    'maintenance_type':maintenance_type,
                    'stage_id':1

                }
                new_request = self.copy(vals)








        return res

class MaintenanceEquipment(models.Model):

    _inherit = 'maintenance.equipment'


    @api.one
    def _get_active_task(self):
        domain = [('equipment_id', '=', self.id), ('stage_id.default_done', '=', False)]
        tasks = self.env['project.task'].search(domain)
        self.active_tasks = len(tasks)

    @api.one
    def _get_ok_calendar(self):
        domain = [('equipment_id', '=', self.id)]
        tasks = self.env['project.task.concurrent'].search(domain)
        self.ok_calendar = True if tasks else False



    allowed_user_ids = fields.Many2many('res.users', string="Allowed Users")
    active_tasks = fields.Integer("Tasks no finished", compute ="_get_active_task")
    ok_calendar = fields.Boolean("Ok Calendar", compute="_get_ok_calendar")
    no_equipment = fields.Boolean("Default no equipment")


    @api.multi
    def copy(self):

        vals = ({'allowed_user_ids': [6,0, [self.allowed_user_ids]]})
        new_equipment = super(MaintenanceEquipment, self).copy(vals)

        return new_equipment

    @api.model
    def create(self, vals):

        equipment = super(MaintenanceEquipment, self).create(vals)
        return equipment



    @api.multi
    def write(self, vals):

        return super(MaintenanceEquipment, self).write(vals)

class ConcurrentTask(models.Model):
    _name="project.task.concurrent"
    _description = "Concurrent Tasks"

    origin_task_id = fields.Many2one("project.task", string="Task Reference(Actual)", help="This task generate concurrent tasks")
    date_end = fields.Datetime(string='Ending Date')
    date_start = fields.Datetime(string='Starting Date')
    task_id = fields.Many2one("project.task", string="Concurrent Task", help="Task concurrent with reference task")
    equipment_id = fields.Many2one("maintenance.equipment", 'Equipment')
    name = fields.Char(related="task_id.name")
    #project_id= fields.Many2one(related="task_id.project_id")
    #activity_id  = fields.Many2one(related="task_id.activity_id")
    #activity_id = fields.Many2one("project.activity",related="task_id.activity_id")# string="Activity")
    #user_ids = fields.Many2many('res.users',
    #                                string='Assigned to')
    user_id = fields.Many2one('res.users', string="Assigned to")
    error = fields.Char("Concurrence type")
    error_color = fields.Integer("Kanban Color")


    def open_task_view(self):

                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'view_task_form2',
                        'res_model': 'project.task',
                        'view_mode': 'form',
                        }

class ProjectTask(models.Model):

    _inherit ="project.task"

    equipment_id = fields.Many2one("maintenance.equipment", 'Equipment')
    allowed_user_ids = fields.Many2many(related="equipment_id.allowed_user_ids", string= "Allowed Users")
        #sobreescribo el campo user_id para eliminar el asignado por defecto y añadir el dominioo
    user_ids = fields.Many2many('res.users',
                              string='Asigned to',
                              index=True, track_visibility='always')
                              #domain="[('id', '!=', allowed_user_ids and  allowed_user_ids[0][2])]")
                              #domain="[('id','in', allowed_user_ids and allowed_user_ids[0][2] or [])]")
    ok_calendar = fields.Boolean ("Ok Calendar", default=True)
    user_id = fields.Many2one('res.users',
                              string='Manager',
                              default=lambda self: self.env.uid,
                              index=True, track_visibility='always')
    #concurrent_task_ids = fields.Many2many("project.task.concurrent", column1="task_id", column2="origin_task_id")

    @api.constrains('equipment_id', 'user_ids')
    def _check_user_ids(self):

        if self.equipment_id and not self.equipment_id.no_equipment and not self.user_ids:
            if not self.stage_id.default_draft :
                raise ValidationError(_('Error ! Task with equiment must be assigned.'))

    @api.onchange('equipment_id')#, 'date_start', 'date_end', 'user_ids')
    def get_user_ids_domain(self):

        if self.equipment_id:
            x = {'domain': {'user_ids': [('id', 'in', [x.id for x in self.allowed_user_ids])]},
                 'value': {'user_ids': []}}
        else:
            x = {'domain': {'user_ids': []},
                 'value': {'user_ids': []}}
        return x


    def get_concurrent(self, user_ids = False, equipment_id = False,
                       date_start = False, date_end = False):

        if isinstance(self.id, models.NewId):
            self_id = self._context['params']['id']
        else:
            self_id = self.id
        equipment_id = equipment_id or self.equipment_id.id

        if self.env['maintenance.equipment'].browse(equipment_id).no_equipment:
            equipment_id = False

        date_start = date_start or self.date_start
        date_end = date_end or self.date_end



        if user_ids:
            user_ids = self.env['res.users'].browse(user_ids[0][2])
        else:
            user_ids = self.user_ids


        concurrent_task_ids = []
        domain = [('origin_task_id','=',self_id)]
        borrar = self.env['project.task.concurrent'].search(domain)
        borrar.unlink()

        if equipment_id:
            domain = [('equipment_id', '=', equipment_id),
                      ('equipment_id.no_equipment','!=', True),
                      ('stage_id.default_done','!=', True),
                      ('id','!=', self_id)]
            pool_tasks = self.env['project.task'].search(domain)
            for task in pool_tasks:
                if (task.date_start < date_start < task.date_end) \
                        or (task.date_start< date_end < task.date_end):
                    vals ={
                        'origin_task_id': self_id,
                        'task_id': task.id,
                        'date_start': task.date_start,
                        'date_end': task.date_end,
                        'equipment_id': task.equipment_id.id,
                        'error': "Concurrent equipment",
                        'error_color':1
                    }
                    concurrent_task_ids += self.env['project.task.concurrent'].create(vals)

        if user_ids:
            domain = [('stage_id.default_done', '!=', True), ('id','!=',self_id),
                      (('|'),
                      ('&', ('date_start', '<', date_start), ('date_end', '>', date_start)),
                      ('&', ('date_start', '<', date_end), ('date_end', '>', date_end)))
                      ]
            domain = [('stage_id.default_done', '!=', True), ('id','!=',self_id),
                      '|',
                      '&', ('date_start', '<', date_end), ('date_end', '>', date_end),
                      '&', ('date_start', '<', date_start), ('date_end', '>', date_start)
            ]

            pool_tasks = self.env['project.task'].search(domain)

            for task in pool_tasks:
                if user_ids:
                #if (task.date_start < date_start < task.date_end) \
                #        or (task.date_start < date_end < task.date_end) or \
                #        (date_start < task.date_start and date_end > task.date_end):

                    for user_id in user_ids:
                        if user_id in task.user_ids:
                            vals ={
                                'origin_task_id': self_id,
                                'task_id': task.id,
                                'user_id': user_id.id,
                                'date_start': task.date_start,
                                'date_end': task.date_end,
                                'error': "Concurrent user",
                                'error_color': 2
                        }
                            concurrent_task_ids += self.env['project.task.concurrent'].create(vals)

            start_dt = Datetime.from_string(date_start)
            end_dt = Datetime.from_string(date_end)

            if start_dt.replace(hour=0, minute=0, second=0).date() != end_dt.replace(hour=23, minute=59, second=59).date():
                raise ValidationError(_('Error ! Your task is 2 days long'))
            for user_id in user_ids:
                employee = self.env['hr.employee'].search([('user_id', '=', user_id.id)])
                calendar = employee.calendar_id
                if employee and calendar:
                    #mio si trabaja ese dia
                    domain_resource = [('user_id', '=', user_id.id)]
                    resource = self.env['resource.resource'].search(domain_resource)
                    is_work_day = resource._iter_work_days(start_dt, end_dt)
                    if is_work_day:

                        calendar = employee.calendar_id
                        intervals = calendar.get_working_intervals_of_day(start_dt=start_dt,
                                                                     end_dt=end_dt,
                                                                     leaves=None,
                                                                     compute_leaves=True,
                                                                     resource_id=resource.id,
                                                                     default_interval=None)

                        duracion_interval = 0
                        day_interval = calendar.get_working_intervals_of_day(
                            start_dt=start_dt.replace(hour=0, minute=0, second=0))
                        if day_interval:
                            day_hours = ''
                            for i in day_interval:
                                i1 = fields.Datetime.context_timestamp(self, i[0])
                                i2 = fields.Datetime.context_timestamp(self, i[1])
                                duracion_interval += (i1 - i2).seconds
                                if day_hours:
                                    day_hours = "%s | %s:%s - %s:%s" % (day_hours, i1.hour, i1.minute, i2.hour, i2.minute)
                                else:
                                    day_hours = "%s:%s - %s:%s" % (i1.hour, i1.minute, i2.hour, i2.minute)
                        else:
                            day_hours="No calendar"

                        if intervals:
                            for interval in intervals:
                                if not (start_dt >= interval[0] and end_dt <= interval[1]):
                                    vals = {
                                        'origin_task_id': self_id,
                                        'task_id': self_id,
                                        'user_id': user_id.id,
                                        'date_start': date_start,
                                        'date_end': date_end,
                                        'error': "Task out of calendar: %s"%day_hours,
                                        'error_color': 3
                                        }
                                    concurrent_task_ids += self.env['project.task.concurrent'].create(vals)
                                    #hago un break para evitar añadir 2 en caso de mañana y ttarde
                                    break
                            duracion_tarea = (end_dt - start_dt).seconds

                            #TODO COMPROBAR SI ESTO ES NECESARIO
                            #compruebo si da tiempo a realizarlo dentro de la jornada

                            if duracion_tarea > duracion_interval:
                                horario = 'Task: %s - Calendar: %s (minutes)'%(duracion_tarea/60, duracion_interval/60)
                                vals = {
                                    'origin_task_id': self_id,
                                    'task_id': self_id,
                                    'user_id': user_id.id,
                                    'date_start': date_start,
                                    'date_end': date_end,
                                    'error': "No time: %s" % horario,
                                    'error_color': 4
                                }
                                concurrent_task_ids += self.env['project.task.concurrent'].create(vals)

                        else:
                            #Si no hay intervalos
                            vals = {
                                'origin_task_id': self_id,
                                'task_id': self_id,
                                'user_id': user_id.id,
                                'date_start': date_start,
                                'date_end': date_end,
                                'error': "ask out of calendar: %s" % day_hours,
                                'error_color': 1
                            }
                            concurrent_task_ids += self.env['project.task.concurrent'].create(vals)
                    else:
                        #si no trbabaja ese dia is_working_day = False
                        vals = {
                            'origin_task_id': self_id,
                            'task_id': self_id,
                            'user_id': user_id.id,
                            'date_start': date_start,
                            'date_end': date_end,
                            'error': "%s no calendar for that day"%user_id.name,
                            'error_color': 5
                        }
                        concurrent_task_ids += self.env['project.task.concurrent'].create(vals)


        if concurrent_task_ids:
            ok_calendar = False
            #si hay tareas concurrentes añado la original para poder visualizar en el calendario de concurrentes
            vals ={
                'origin_task_id': self_id,
                'task_id': self_id,
                'date_start': date_start,
                'date_end': date_end,
                'equipment_id': equipment_id,
                'error': "Reference Task",
                'error_color':0
            }
            concurrent_task_ids += self.env['project.task.concurrent'].create(vals)
        else:
            ok_calendar = True
        return ok_calendar

    def open_concurrent(self):

        return {
                'type': 'ir.actions.act_window',
                'name': 'open.concurring.tasks',
                'res_model': 'project.task.concurrent',
                'view_mode': 'tree,form,calendar',
                'domain': [('origin_task_id','=',self.id)]}

    def calc_ok(self):
        self.get_concurrent()

    def act_vals(self, vals):
        if vals.get('date_start'):
            self.date_start = vals.get('date_start')
        if vals.get('date_end'):
            self.date_end = vals.get('date_end')
        if vals.get('equipment_id'):
            self.equipment_id = vals.get('equipment_id')
        if vals.get('user_ids'):
            self.user_ids = vals.get('user_ids')

    @api.multi
    def write(self, vals):

        for task in self:
            if task.project_id or 'project_id' in vals:
                equipment_id = False
                if 'equipment_id' in vals:
                    if vals['equipment_id'] > 1:
                        if not vals.get('user_ids', False):
                            raise UserError(_('You must assigned employees if you set equipment'))
                        else:
                            equipment_id=vals['equipment_id']
                    else:
                        equipment_id= False
                else:
                    equipment_id = task.equipment_id.id



                if not task.no_schedule:
                    date_start = vals.get('date_start', False) or task.date_start
                    date_end = vals.get('date_end', False) or task.date_end
                    user_ids = vals.get('user_ids', False)
                    vals['ok_calendar'] = task.get_concurrent(user_ids,
                                                              equipment_id,
                                                              date_start,
                                                              date_end
                                                              )
                else:
                    vals['ok_calendar'] = True
                if 'stage_id' in vals:
                    stage_id = self.env['project.task.type'].browse(vals.get('stage_id'))
                    if not task.ok_calendar and not stage_id.default_draft and not task.no_schedule:
                            raise ValidationError(
                                _('Error stage. Concurrent Task Error'))

        result = super(ProjectTask, self).write(vals)
        return result

class ReportProjectActivityTaskUser(models.Model):
    _inherit = "report.project.task.user"

    equipment_id = fields.Many2one("maintenance.equipment", 'Equipment', group_operator='avg', readonly=True)

    def _select(self):
        return super(ReportProjectActivityTaskUser, self)._select() + """,
            equipment_id as equipment_id
            """

    def _group_by(self):
        return super(ReportProjectActivityTaskUser, self)._group_by() + """,
            equipment_id
            """


