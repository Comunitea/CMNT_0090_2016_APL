# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError

class MaintenanceEquipment(models.Model):

    _inherit = 'maintenance.equipment'


    @api.one
    def _get_active_task(self):
        domain = [('equipment_id', '=', self.id), ('done', '=', False)]
        tasks = self.env['project.task'].search(domain)
        self.active_tasks = len(tasks)

    @api.one
    def _get_ok_calendar(self):
        domain = [('equipment_id', '=', self.id), ('ok_calendar', '=', True), ('done','=', False)]
        tasks = self.env['project.task'].search(domain)
        self.ok_calendar = self.tasks and self.tasks[0].ok_calendar or False

    allowed_user_ids = fields.Many2many('res.users', string="Allowed Users")
    active_tasks = fields.Integer("Tasks no finished", compute ="_get_active_task")
    ok_calendar = fields.Boolean("Ok Calendar", compute="_get_ok_calendar")



    @api.multi
    def copy(self):
        import pdb; pdb.set_trace()

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
    user_ids = fields.Many2many('res.users',
                                string='Assigned to')
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


    @api.one
    def _get_ok_calendar(self):

        if not self.date_start or not self.date_end or not self.equipment_id:
            self.ok_calendar = True
        else:
            self.ok_calendar = self.get_concurrent()

    equipment_id = fields.Many2one("maintenance.equipment", 'Equipment')
    allowed_user_ids = fields.Many2many(related="equipment_id.allowed_user_ids", string= "Allowed Users")
        #sobreescribo el campo user_id para eliminar el asignado por defecto y añadir el dominioo
    user_ids = fields.Many2many('res.users',
                              string='Assigned to',
                              index=True, track_visibility='always')
                              #domain="[('id', '!=', allowed_user_ids and  allowed_user_ids[0][2])]")
                              #domain="[('id','in', allowed_user_ids and allowed_user_ids[0][2] or [])]")

    ok_calendar = fields.Boolean ("Ok Calendar", compute ="_get_ok_calendar")

    user_id = fields.Many2one('res.users',
                              string='Responsable',
                              default=lambda self: self.env.uid,
                              index=True, track_visibility='always')
    #concurrent_task_ids = fields.Many2many("project.task.concurrent", column1="task_id", column2="origin_task_id")

    @api.onchange('equipment_id')#, 'date_start', 'date_end', 'user_ids')
    def get_user_ids_domain(self):

        if self.equipment_id:
            x = {'domain': {'user_ids': [('id', 'in', [x.id for x in self.allowed_user_ids])]}}
        else:
            x = {'domain': {'user_ids': []}}
        return x


    def get_concurrent(self):

        concurrent_task_ids = []
        domain = [('origin_task_id','=',self.id)]
        borrar =self.env['project.task.concurrent'].search(domain)
        borrar.unlink()
        if not self.date_start or not self.date_end or not self.equipment_id:
            return False

        domain = [('equipment_id', '=',self.equipment_id.id),
                  ('stage_id','!=',6), ('id','!=',self.id)]
        pool_tasks = self.env['project.task'].search(domain)
        for task in pool_tasks:
            if (task.date_start<= self.date_start <= task.date_end) \
                    or (task.date_start<= self.date_end <= task.date_end):
                vals ={
                    'origin_task_id': self.id,
                    'task_id': task.id,
                    'date_start': task.date_start,
                    'date_end': task.date_end,
                    'equipment_id': task.equipment_id.id,
                    'error': "Equipo Ocupado"
                }
                concurrent_task_ids += self.env['project.task.concurrent'].create(vals)

        domain = [('date_start', '>=',self.date_start),('date_start','<=',self.date_end), ('stage_id', '!=', 6), ('date_end','<=',self.date_end), ('date_end','<=',self.date_end), ('id','!=',self.id)]
        pool_tasks = self.env['project.task'].search(domain)
        for task in pool_tasks:
            for user_id in self.user_ids:
                if user_id in task.user_ids:
                    vals ={
                        'origin_task_id': self.id,
                        'task_id': task.id,
                        'user_id': user_id.id,
                        'date_start': task.date_start,
                        'date_end': task.date_end,
                        'error': "Usuario Concurrente"
                }
                    concurrent_task_ids += self.env['project.task.concurrent'].create(vals)
        #TODO COMPROBAR SI EL USUARIO ASIGANDO ESTA Y SI ESTA EN HORARIO
        print concurrent_task_ids
        if concurrent_task_ids:
            #si hay tareas concurrentes añado la original para poder viusualizar en el calendario
            vals ={
                'origin_task_id': self.id,
                'task_id': self.id,
                'user_id': self.user_id.id,
                'date_start': self.date_start,
                'date_end': self.date_end,
                'equipment_id': self.equipment_id.id,
                'error': "Referencia"
            }
            concurrent_task_ids += self.env['project.task.concurrent'].create(vals)
            return False
        return True


    def open_concurrent(self):

        return {
                'type': 'ir.actions.act_window',
                'name': 'open.concurring.tasks',
                'res_model': 'project.task.concurrent',
                'view_mode': 'tree,form,calendar',
                'domain': [('origin_task_id','=',self.id)]}


    @api.multi
    def write(self, vals):
        print "OK_calendar %s" %self.ok_calendar
        if not self.ok_calendar:
            print "OK_calendar %s" %self.ok_calendar
            print "stage_id %s"%vals.get('stage_id')
            if vals.get('stage_id')>4:
                raise UserError(_('You cannot change the state because you have concurrent tasks\n or incomplete fields'))

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


