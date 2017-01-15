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

    origin_task_id = fields.Many2one("project.task", string="Task Reference(Actual)", help="Tarea actual")
    date_end = fields.Datetime(string='Ending Date')
    date_start = fields.Datetime(string='Starting Date')
    task_id = fields.Many2one("project.task", string="Concurrent Task", help="Tarea en conflicto con la actual")
    equipment_id = fields.Many2one("maintenance.equipment", 'Equipment')
    name = fields.Char(related="task_id.name")
    #project_id= fields.Many2one(related="task_id.project_id")
    #activity_id  = fields.Many2one(related="task_id.activity_id")
    #activity_id = fields.Many2one("project.activity",related="task_id.activity_id")# string="Activity")
    #user_ids = fields.Many2many('res.users',
    #                                string='Assigned to')
    user_id = fields.Many2one('res.users', string="Assigned to")
    error = fields.Char("Tipo de Concurrencia")



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
                              string='Asignado a',
                              index=True, track_visibility='always')
                              #domain="[('id', '!=', allowed_user_ids and  allowed_user_ids[0][2])]")
                              #domain="[('id','in', allowed_user_ids and allowed_user_ids[0][2] or [])]")

    ok_calendar = fields.Boolean ("Ok Calendar")

    user_id = fields.Many2one('res.users',
                              string='Responsable',
                              default=lambda self: self.env.uid,
                              index=True, track_visibility='always')
    #concurrent_task_ids = fields.Many2many("project.task.concurrent", column1="task_id", column2="origin_task_id")

    @api.constrains('equipment_id', 'user_ids')
    def _check_user_ids(self):
        if self.equipment_id and not self.user_ids:
            raise ValidationError(_('Error ! Task with equiment must be assigned.'))


    @api.onchange('date_start', 'date_end', 'user_ids')
    def _get_ok_calendar(self):

        self.ok_calendar = False




    @api.onchange('equipment_id')#, 'date_start', 'date_end', 'user_ids')
    def get_user_ids_domain(self):

        if self.equipment_id:
            x = {'domain': {'user_ids': [('id', 'in', [x.id for x in self.allowed_user_ids])]},
                 'value': {'user_ids': []}}
        else:
            x = {'domain': {'user_ids': []},
                 'value': {'user_ids': []}}
        return x


    def get_concurrent(self, self_id = False, equipment_id = False, 
                       date_start = False, date_end = False):

        
        self_id = self_id or self.id
        equipment_id = equipment_id or self.equipment_id.id
        date_start = date_start or self.date_start
        date_end = date_end or self.date_end

        concurrent_task_ids = []
        domain = [('origin_task_id','=',self_id)]
        borrar = self.env['project.task.concurrent'].search(domain)
        borrar.unlink()

        if not (date_start and date_end and equipment_id):
            return False

        domain = [('equipment_id', '=', equipment_id),
                  ('equipment_id.no_equipment','!=', True),
                  ('stage_id.default_done','!=', True),
                  ('id','!=', self_id)]
        pool_tasks = self.env['project.task'].search(domain)
        for task in pool_tasks:
            if (task.date_start<= date_start <= task.date_end) \
                    or (task.date_start<= date_end <= task.date_end):
                vals ={
                    'origin_task_id': self_id,
                    'task_id': task.id,
                    'date_start': task.date_start,
                    'date_end': task.date_end,
                    'equipment_id': task.equipment_id.id,
                    'error': "Equipo Ocupado"
                }
                concurrent_task_ids += self.env['project.task.concurrent'].create(vals)

        domain = [('stage_id.default_done', '!=', True),
                  ('id','!=',self_id)]
        pool_tasks = self.env['project.task'].search(domain)
        for task in pool_tasks:
            if (task.date_start <= date_start <= task.date_end) \
                    or (task.date_start <= date_end <= task.date_end):

                for user_id in self.user_ids:
                    if user_id in task.user_ids:
                        vals ={
                            'origin_task_id': self_id,
                            'task_id': task.id,
                            'user_id': user_id.id,
                            'date_start': task.date_start,
                            'date_end': task.date_end,
                            'error': "Usuario Concurrente"
                    }
                        concurrent_task_ids += self.env['project.task.concurrent'].create(vals)



        start_dt = Datetime.from_string(date_start)
        end_dt = Datetime.from_string(date_end)
        for user_id in self.user_ids:
            employee = self.env['hr.employee'].search([('user_id', '=', user_id.id)])
            if employee:
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
                                                                 resource_id=resource,
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
                        day_hours="Sin horario"

                    if intervals:
                        for interval in intervals:
                            if not (start_dt >= interval[0] and end_dt <= interval[1]):
                                vals = {
                                    'origin_task_id': self_id,
                                    'task_id': self_id,
                                    'user_id': user_id.id,
                                    'date_start': date_start,
                                    'date_end': date_end,
                                    'error': "Horario fuera de jornada: %s"%day_hours
                                    }
                                concurrent_task_ids += self.env['project.task.concurrent'].create(vals)
                                #hago un break para evitar añadir 2 en caso de mañana y ttarde
                                break
                        duracion_tarea = (end_dt - start_dt).seconds

                        #TODO COMPROBAR SI ESTO ES NECESARIO
                        #compruebo si da tiempo a realizarlo dentro de la jornada

                        if duracion_tarea > duracion_interval:
                            horario = 'Tarea: %s - Jornada: %s (minutos)'%(duracion_tarea/60, duracion_interval/60)
                            vals = {
                                'origin_task_id': self_id,
                                'task_id': self_id,
                                'user_id': user_id.id,
                                'date_start': date_start,
                                'date_end': date_end,
                                'error': "No da tiempo: %s" % horario
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
                            'error': "Horario fuera de jornada: %s" % day_hours
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
                        'error': "%s no trabaja ese dia"%user_id.name
                    }
                    concurrent_task_ids += self.env['project.task.concurrent'].create(vals)


        if concurrent_task_ids:
            return False
            #si hay tareas concurrentes añado la original para poder viusualizar en el calendario
            vals ={
                'origin_task_id': self_id,
                'task_id': self_id,
                'date_start': date_start,
                'date_end': date_end,
                'equipment_id': equipment_id,
                'error': "Referencia"
            }
            # concurrent_task_ids += self.env['project.task.concurrent'].create(vals)

        return True

    def open_concurrent(self):

        return {
                'type': 'ir.actions.act_window',
                'name': 'open.concurring.tasks',
                'res_model': 'project.task.concurrent',
                'view_mode': 'tree,form,calendar',
                'domain': [('origin_task_id','=',self.id)]}

    def calc_ok(self):

        self.get_concurrent()


    @api.multi
    def write(self, vals):

        if vals.get('date_start') or vals.get('date_end') or vals.get('user_ids'):
            vals['ok_calendar'] = self.get_concurrent(self.id,
                                                      vals.get('equiment_id', False),
                                                      vals.get('date_start', False),
                                                      vals.get('date_end', False))

        if vals.get('stage_id') and not self.ok_calendar:
            raise UserError(_('You cannot change the state because you have concurrent tasks\n or incomplete fields'))

        if vals.get('equipment_id', False) and not vals.get('user_ids', False):
            raise UserError(_('You assigned employees if you set equipment'))

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


