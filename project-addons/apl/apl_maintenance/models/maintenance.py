# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.fields import Datetime, Date
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

    _name = "project.task.concurrent"
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
    is_reference = fields.Boolean('is reference task', default=False)


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
    user_ids = fields.Many2many('res.users', string='Asiganda a',
                                index=True, track_visibility='always', required=True)
    ok_calendar = fields.Boolean ("Ok Calendar", default=True)
    task_day = fields.Datetime("task day")

    @api.constrains('equipment_id', 'user_ids')
    def _check_user_ids(self):

        if self.equipment_id and not self.equipment_id.no_equipment and not self.user_ids:
            if not self.stage_id.default_draft :
                raise ValidationError(_('Error ! Task with equiment must be assigned.'))

    @api.onchange('equipment_id')#, 'date_start', 'date_end', 'user_ids')
    def get_user_ids_domain(self):

        if self.equipment_id:
            x = {'domain': {'user_ids': [('id', 'in', [x.id for x in self.equipment_id.allowed_user_ids])]},
                 'value': {'user_ids': []}}
        else:
            x = {'domain': {'user_ids': []},
                 'value': {'user_ids': []}}

        if self.stage_id.id and not self.stage_id.default_draft:
            x['warning'] = {'title': _('Warning'),
                            'message': _('You are changing equipment in wrong stage.')}
        return x

    def get_concurrent(self, user_ids=False, equipment_id=False,
                       date_start=False, date_end=False, self_id=False):

        def new_concurrent(origin_task_id, task_id, user_id, date_start, date_end, equipment_id, error, error_color, is_reference= False):
            vals = {
                'origin_task_id': origin_task_id,
                'task_id': task_id,
                'user_id': user_id,
                'date_start': date_start,
                'date_end': date_end,
                'equipment_id': equipment_id,
                'error': error,
                'error_color': error_color,
                'is_reference': is_reference
            }
            new_task = self.env['project.task.concurrent'].create(vals)
            return new_task.id

        if not self_id:
            if isinstance(self.id, models.NewId):
                self_id = self._context['params']['id']
            else:
                self_id = self.id

        equipment_id = equipment_id or self.equipment_id.id
        date_start = date_start or self.date_start
        date_end = date_end or self.date_end

        if user_ids:
            user_ids = self.env['res.users'].browse(user_ids)
        else:
            user_ids = self.user_ids
        concurrent_task_ids = []

        # Borro las tareas concurrentes
        domain = [('origin_task_id', '=', self_id)]
        to_unlink = self.env['project.task.concurrent'].search(domain)
        to_unlink.unlink()
        add_reference = False
        pool_tasks_equipment = False
        if equipment_id:
            # Compruebo que el equipo no este en dos tareas al mismo tiempo

            domain = [('equipment_id', '=', equipment_id),
                      ('equipment_id.no_equipment','!=', True),
                      ('stage_id.default_running','=', True),
                      ('id','!=', self_id)]
            pool_tasks_equipment = self.env['project.task'].search(domain)
            for task in pool_tasks_equipment:
                if (task.date_start < date_start < task.date_end) \
                        or (task.date_start< date_end < task.date_end):

                    new_id = new_concurrent(self_id, task.id, False, task.date_start, task.date_end,
                                            task.equipment_id.id, "Equipamiento no disponible", 1,
                                            is_reference=False)

                    concurrent_task_ids += [new_id]
                    add_reference = True

        if not equipment_id and not pool_tasks_equipment:
            print "---------Equipamiento OK"

        if user_ids:
            # Compruebo que los usuarios no esten en dos tareas al mismo tiempo
            import ipdb; ipdb.set_trace()
            new_date_end = Datetime.from_string(date_end) - timedelta(minutes=1)
            new_date_end = Datetime.to_string(new_date_end)
            new_date_start = Datetime.from_string(date_start) + timedelta(minutes=1)
            new_date_start = Datetime.to_string(new_date_start)
            domain = [('no_schedule', '=', False), ('stage_id.default_running', '=', True), ('id', '!=', self_id),
                      '|',
                      '&', ('date_start', '<=', new_date_end), ('date_end', '>=', new_date_start),
                      '&', ('date_start', '<=', new_date_start), ('date_end', '>=', new_date_start),

                     ]

            print domain
            pool_tasks = self.env['project.task'].search(domain)

            new_id = False
            for task in pool_tasks:
                print task.name
                for user_id in user_ids:
                    print user_id.name
                    if user_id in task.user_ids:
                        new_id = new_concurrent(self_id, task.id, user_id.id, task.date_start, task.date_end,
                                                False, "Usuario Ocupado", 1,
                                                is_reference=False)
                        concurrent_task_ids += [new_id]
                        add_reference = True

            if not new_id:
                print "---------Tareas OK"

            start_dt = Datetime.from_string(date_start)
            end_dt = Datetime.from_string(date_end)
            start_d = Date.from_string(date_start)
            if start_dt.replace(hour=0, minute=0, second=0).date() != end_dt.replace(hour=23, minute=59, second=59).date():
                raise ValidationError(_('Error ! Your task is 2 days long'))

            for user_id in user_ids:
                # compruebo si trabaja ese dia.
                domain_resource = [('user_id', '=', user_id.id)]
                resource = self.env['resource.resource'].search(domain_resource)
                if resource and start_dt != end_dt:
                    is_work_day = resource.is_work_day(start_dt)

                    if is_work_day:
                        print "--------Trabaja ese dia"
                        import ipdb; ipdb.set_trace()
                        employee = self.env['hr.employee'].search([('user_id', '=', user_id.id)])
                        calendar = employee.calendar_id
                        intervals = calendar.get_working_intervals_of_day(start_dt=start_dt,
                                                                          end_dt=end_dt,
                                                                          compute_leaves=True,
                                                                          resource_id=resource.id)
                        duracion_interval = 0


                        if intervals:
                            work_sec = (intervals[0][1]-intervals[0][0]).seconds
                            task_sec = (end_dt - start_dt).seconds
                            if task_sec > work_sec:
                                day_interval = calendar.get_working_intervals_of_day(
                                    start_dt=start_dt.replace(hour=0, minute=0, second=0),
                                    compute_leaves=True, resource_id=resource.id)
                                day_hours = ''
                                for work_interval in day_interval:

                                    i1 = fields.Datetime.context_timestamp(self, work_interval[0])
                                    i2 = fields.Datetime.context_timestamp(self, work_interval[1])
                                    duracion_interval += (i1 - i2).seconds

                                    day_hours += "%02d:%02d - %02d:%02d " % (i1.hour, i1.minute, i2.hour, i2.minute)

                                print "-------Fuera de horario ese dia"
                                new_id = new_concurrent(self_id, self_id, user_id.id, date_start,
                                                        date_end,
                                                        False, "Fuera de horario. Disponible %s" % day_hours, 3,
                                                        is_reference=False)

                                concurrent_task_ids += [new_id]

                        else:
                            print "-------No trabaja ese dia"
                            new_id = new_concurrent(self_id, self_id, user_id.id, date_start,
                                                    date_end,
                                                    False, "Fuera de horario", 1,
                                                    is_reference=False)

                            concurrent_task_ids += [new_id]

                    else:
                        print "-------No trabaja ese dia"
                        new_id = new_concurrent(self_id, self_id, user_id.id, False, False,
                                                False, "No trabaja el dia %s"%start_d, 3,is_reference=False)

                        concurrent_task_ids += [new_id]


                else:
                    continue

        if concurrent_task_ids:
            ok_calendar = False
            if add_reference:
                new_id = new_concurrent(self_id, self_id, False, date_start,
                                        date_end,
                                        False, "Tarea de referencia", 0,
                                        is_reference=True)
                concurrent_task_ids += [new_id]
        else:
            ok_calendar = True
        return ok_calendar

    def open_concurrent(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'open.concurring.tasks',
                'res_model': 'project.task.concurrent',
                'view_mode': 'tree,form,calendar',
                'domain': [('origin_task_id', '=', self.id)]}

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

    def getval(self, vals, field, type = False):
        if field in vals:
            if type =='o2m' or type== 'm2m':
                new_value = vals.get(field)[0][2]
            else:
                new_value = vals[field]
        else:
            if type == 'm2o':
                new_value = self[field].id
            elif type =='o2m' or type =='m2m':
                new_value = [x.id for x in self[field]]
            else:
                new_value = self[field]



        return new_value

    def refresh_follower_ids(self, new_follower_ids = []):
        message_follower_ids = []
        if new_follower_ids:


            to_append = []
            to_unlink = []
            partner_ids = []
            follower_ids =[]
            for x in self.message_follower_ids:
                follower_ids += [x.partner_id.id]


            for us in new_follower_ids:
                partner_id = self.env['res.users'].browse(us).partner_id.id
                partner_ids += [partner_id]
                to_append += [partner_id]

            to_append += [self.user_id.partner_id.id]
            to_append += [self.create_uid.partner_id.id]
            to_append = list(set(to_append))


            for follower in self.message_follower_ids:
                to_unlink += [follower.id]
            res = self.env['mail.followers'].browse(to_unlink).unlink()

            for new_follower_id in to_append:
                message_follower_id, po = self.message_follower_ids._add_follower_command('project.task',
                                                                                          [self.id],
                                                                                          {new_follower_id: None},
                                                                                          {}, True)
                message_follower_ids += message_follower_id

            return message_follower_ids


    @api.model
    def create(self, vals):

        res = super(ProjectTask, self).create(vals)

        if 'user_ids' in vals:
            userf_ids = vals['user_ids'][0][2]
            vals['message_follower_ids'] = res.refresh_follower_ids(new_follower_ids=userf_ids)
            vals2 = {'message_follower_ids': vals['message_follower_ids'] }
            res.write(vals2)
        return res




    @api.multi
    def write(self, vals):

        if self.user_id.id != self.env.user.id and self.env.user.id != 1:
            if 'stage_id' in vals:
                new_vals = {'stage_id': vals['stage_id']}
                return super(ProjectTask, self).write(new_vals)
            else:
                raise ValidationError ("No tienes permisos para cambiar esta tarea")


        for task in self:
            project_id = task.getval(vals, 'project_id', 'm2o')
            equipment_id = task.getval(vals, 'equipment_id', 'm2o')
            no_schedule = task.getval(vals, 'no_schedule')
            date_start = task.getval(vals, 'date_start')
            date_end = task.getval(vals, 'date_end')
            new_activity_id = task.getval(vals, 'new_activity_id', 'm2o')
            user_ids = task.getval(vals, 'user_ids', 'o2m')
            new_activity_created = task.getval(vals, 'new_activity_created', 'm2o')
            activity_id = task.getval(vals, 'activity_id', 'm2o')

            vals['task_day'] = fields.Date.from_string(date_start)

            if 'user_ids' in vals:
                userf_ids = vals['user_ids'][0][2]
                vals['message_follower_ids'] = task.refresh_follower_ids(new_follower_ids = userf_ids)

            if not user_ids:
                raise UserError(_('You must assigned employees'))

            if no_schedule:
                ok_calendar = True
            else:
                ok_calendar = task.get_concurrent(user_ids, equipment_id, date_start, date_end)

            vals['ok_calendar'] = ok_calendar

            if 'stage_id' in vals:

                stage_id = self.env['project.task.type'].browse(vals.get('stage_id'))
                if not ok_calendar and not stage_id.default_draft:
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


