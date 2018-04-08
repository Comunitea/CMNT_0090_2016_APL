# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.fields import Datetime, Date
import pytz



class MaintenancePreventive(models.Model):
    _name = 'maintenance.preventive'

    @api.multi
    def _compute_next_maintenance(self):
        date_now = fields.Date.context_today(self)
        for preventive in self:
            next_maintenance_todo = self.env['maintenance.request'].search([
                ('preventive_id', '=', preventive.id),
                ('stage_id.done', '!=', True)], order="request_date asc", limit=1)
            last_maintenance_done = self.env['maintenance.request'].search([
                ('preventive_id', '=', preventive.id),  ('stage_id.done', '=', True)], order="close_date desc", limit=1)

            equipment = preventive.equipment_id
            if next_maintenance_todo and last_maintenance_done:
                next_date = next_maintenance_todo.request_date
                date_gap = fields.Date.from_string(next_maintenance_todo.request_date) - fields.Date.from_string(
                    last_maintenance_done.close_date)
                # If the gap between the last_maintenance_done and the next_maintenance_todo one is bigger than 2 times the period and next request is in the future
                # We use 2 times the period to avoid creation too closed request from a manually one created
                if date_gap > timedelta(0) and date_gap > timedelta(
                        days=equipment.period) * 2 and fields.Date.from_string(
                        next_maintenance_todo.request_date) > fields.Date.from_string(date_now):
                    # If the new date still in the past, we set it for today
                    if fields.Date.from_string(last_maintenance_done.close_date) + timedelta(
                            days=equipment.period) < fields.Date.from_string(date_now):
                        next_date = date_now
                    else:
                        next_date = fields.Date.to_string(
                            fields.Date.from_string(last_maintenance_done.close_date) + timedelta(
                                days=equipment.period))
            elif next_maintenance_todo:
                next_date = next_maintenance_todo.request_date
                date_gap = fields.Date.from_string(next_maintenance_todo.request_date) - fields.Date.from_string(
                    date_now)
                # If next maintenance to do is in the future, and in more than 2 times the period, we insert an new request
                # We use 2 times the period to avoid creation too closed request from a manually one created
                if date_gap > timedelta(0) and date_gap > timedelta(days=equipment.period) * 2:
                    next_date = fields.Date.to_string(
                        fields.Date.from_string(date_now) + timedelta(days=equipment.period))
            elif last_maintenance_done:
                next_date = fields.Date.from_string(last_maintenance_done.close_date) + timedelta(days=equipment.period)
                # If when we add the period to the last maintenance done and we still in past, we plan it for today
                if next_date < fields.Date.from_string(date_now):
                    next_date = date_now
            else:
                next_date = fields.Date.to_string(fields.Date.from_string(date_now) + timedelta(days=equipment.period))

            preventive.next_action_date = next_date

    @api.multi
    def name_get(self):
        """Use the company name and template as name."""
        res = []
        for record in self:
            res.append(
                (record.id, "%s - %s" % (record.equipment_id.name,
                                         record.name)))
        return res

    name = fields.Char("Name")
    equipment_id = fields.Many2one('maintenance.equipment')
    maintenance_duration = fields.Float(help="Maintenance Duration in minutes and seconds.")
    period = fields.Integer('Days between each preventive maintenance')
    next_action_date = fields.Date(compute='_compute_next_maintenance', string='Date of the next preventive maintenance', store=True)
    start_hour = fields.Char("Start hour", help ="Hora por defecto a la que se programa el mantenimiento (Hora: Minuto) 08:00:00")
    planned_cost = fields.Float("Coste previsto", help="Coste previsto para este mantenimiento. Se exporta a la tarea que se genera", required=True)

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    preventive_id = fields.Many2one('maintenance.preventive', "Preventive")
    maintenance_type = fields.Selection(selection_add=[('programmed', 'Programmed')])
    task_id = fields.Many2one('project.task', 'Tarea asociada')

    @api.model
    def get_activity_values(self, project_id=False, maintenance_type=False):

         return {   'project_id':project_id.id,
                    'name': self.preventive_id and self.preventive_id.display_name or self.display_name,
                    'user_id': self.equipment_id.technician_user_id.id,
                    'request_type': maintenance_type or self.maintenance_type}

    @api.model
    def get_task_values(self):
        project_id = self.equipment_id.project_id
        if not project_id:
            raise ValidationError(_('Error ! Equipment must be assigned to project.'))

        name = self.name + " " + self.schedule_date
        if self.preventive_id:
            activity_name = self.maintenance_type + '[%s]'%self.preventive_id
            maintenance_duration = self.preventive_id.maintenance_duration
            planned_cost = self.preventive_id.planned_cost
        else:
            activity_name = self.maintenance_type
            maintenance_duration = self.equipment_id.maintenance_duration
            planned_cost = 0.01

        start_dt = fields.Datetime.from_string(self.schedule_date)
        end_dt = start_dt + timedelta(minutes=(maintenance_duration - int(maintenance_duration)) * 60) + timedelta(hours=int(maintenance_duration))
        user_id = self.equipment_id.technician_user_id.id
        activity_id = project_id.activity_ids.filtered(lambda x: x.request_type == activity_name)
        if not activity_id:
            activity_id = self.env['project.activity'].create(self.get_activity_values(project_id, activity_name))

        vals = {
            'name': name,
            'project_id': project_id.id,
            'equipment_id': self.equipment_id.id,
            'maintenance_request_id': self.id,
            'activity_id': activity_id.id,
            'user_id': user_id,
            'user_ids': [(6, 0, [user_id])],
            'date_start': self.schedule_date,# + start_hour,
            'date_end': end_dt,
            'planned_hours': maintenance_duration,
            'task_planned_cost': planned_cost,

        }
        return vals

    @api.model
    def create(self, vals):
        new_request = super(MaintenanceRequest, self).create(vals)
        ctx = self._context.copy()
        ctx.update({'from_maintenance_request': True})
        new_task = self.env['project.task'].with_context(ctx).create(new_request.get_task_values())
        new_task.message_post(
            body="Esta tarea ha sido creada de: <a href=# data-oe-model=maintenance.request data-oe-id=%d>%s</a>" % (
            new_request.id, new_request.display_name))
        new_request.task_id = new_task
        ok_calendar, ok_calendar_message = new_task.get_concurrent()
        if not ok_calendar:
            new_task.message_post(body=ok_calendar_message)
        elif ok_calendar:
            new_request.stage_id = self.env['maintenance.stage'].search(
                [('sequence', '>', new_request.stage_id.sequence)], limit=1)
        return new_request

    @api.multi
    def unlink(self):
        self.mapped('task_id').unlink()
        return super(MaintenanceRequest, self).unlink()

    @api.multi
    def write(self, vals):
        if 'stage_id' in vals:
            restart_stage = self.env['maintenance.stage'].search([], limit=1)
            stage = self.env['maintenance.stage'].browse(vals.get('stage_id'))
            if restart_stage == self.stage_id and stage.done:
                raise ValidationError('No puedes realizar un mantenimiento no programado')
            if stage.done:
                stage_domain = [('default_done', '=', True)]
            elif stage != restart_stage:
                stage_domain = [('default_running', '=', True)]
            else:
                stage_domain = [('default_draft', '=', True)]

            stage_id = self.task_id.stage_find([], domain=stage_domain)
            ctx = self._context.copy()
            ctx.update({'from_maintenance_request': True})
            write_task = self.sudo().task_id.with_context(ctx).write({'stage_id': stage_id or restart_stage.id})
            if not write_task:
                self.message_post(
                    body="No se ha podido programar el mantenimiento <em>%s</em> para el <b>%s</b>. Comprueba la tarea creada" % (
                    self.name, self.schedule_date))
                vals['stage_id'] = restart_stage.id
            else:
                self.task_id.message_post(
                    body="El usuario <em>%s</em> ha cambiado el estado desde el mantenimiento asociado" % (self.env.user.name)
                    )
        res = super(MaintenanceRequest, self).write(vals)
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
    active = fields.Boolean(default=True, help="The active field allows you to hide the category without removing it.")
    preventive_ids = fields.One2many('maintenance.preventive', 'equipment_id', string="Preventives")
    project_id = fields.Many2one('project.project', 'Proyecto asociado')

    def return_create_vals(self, date, schedule_date=False, preventive_id=False):
        if not date:
            date = fields.Date.today()

        if not schedule_date:
            schedule_date = date

        if preventive_id:
            name = preventive_id.display_name
            type = "programmed"
            start_hour = " " + preventive_id.start_hour
            maintenance_duration = preventive_id.maintenance_duration
        else:
            name = u'Mantenimiento preventivo - %s' % self.name
            type = 'preventive'
            maintenance_duration = self.maintenance_duration
            start_hour = ' 07:00'

        schedule_date = schedule_date + start_hour
        vals = {
            'name': name,
            'request_date': date,
            'schedule_date': schedule_date,
            'category_id': self.category_id.id,
            'equipment_id': self.id,
            'maintenance_type': type,
            'owner_user_id': self.env.uid or self.owner_user_id.id,
            'technician_user_id': self.technician_user_id.id,
            'duration': maintenance_duration,
            'preventive_id': preventive_id and preventive_id.id or False
        }
        return vals

    def _create_new_request(self, date, schedule_date=False, preventive_id=False):
        self.ensure_one()
        self.env['maintenance.request'].create(self.return_create_vals(date=date, schedule_date=schedule_date, preventive_id=preventive_id))

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

    @api.model
    def _cron_generate_requests(self):
        """
            Generates maintenance request on the next_action_date or today if none exists
        """
        super(MaintenanceEquipment, self)._cron_generate_requests()
        for preventive in self.env['maintenance.preventive'].search([('period', '>', 0)]):
            next_prog_requests = self.env['maintenance.request'].search_read([('stage_id.done', '=', False),
                                                                              ('preventive_id', '=', preventive.id),
                                                                              ])
            if not next_prog_requests:
                preventive.equipment_id._create_new_request(fields.Date.today(), preventive.next_action_date,
                                                            preventive_id=preventive)



