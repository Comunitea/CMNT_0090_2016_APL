# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError

class BatchChangelineUser(models.TransientModel):
    _name = "batch.change.line.user"
    _rec_name = 'user_id'

    wizard_id = fields.Many2one('project.task.batch.change.wz', string="Wizard")
    selected = fields.Boolean("Si/No", default=True)
    user_id = fields.Many2one('res.users', 'Usuario')

class BatchChangeprojectTask(models.TransientModel):
    _name ="batch.change.project.task"

    wizard_id = fields.Many2one('project.task.batch.change.wz', string="Wizard")
    selected = fields.Boolean("Si/No", default=True)
    task_id = fields.Many2one('project.task')

class ProjectTaskBatchChangeWz(models.TransientModel):

    _name = 'project.task.batch.change.wz'

    @api.model
    def default_get(self, fields):

        res = super(ProjectTaskBatchChangeWz, self).default_get(fields)
        res.update({'task_ids': self._context['active_ids']})
        return res

    user_id = fields.Many2one('res.users')
    user_ids = fields.Many2many('res.users', 'task_batch_res_users_rel', 'wizard_id', 'user_id', string="Asignado a")
    activity_id = fields.Many2one('project.activity')
    equipment_id = fields.Many2one('maintenance.equipment')
    task_ids = fields.Many2many('project.task', 'task_batch_project_task_rel', 'wizard_id', 'task_id', string="Aplicar a")

    def change_values(self):

        tasks = []
        for task in self.task_ids.filtered(lambda x: x.stage_id.default_draft):
            tasks.append(task.id)
            if self.user_id:
                task.user_id = self.user_id

            if self.activity_id:
                task.activity_id = self.activity_id
                task.onchange_activity_id()

            if self.equipment_id:
                task.equiment_id = self.equipment_id

            if self.user_ids:
                task.user_ids = self.user_ids

        return {
                'name': 'Tareas en lote',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'project.task',
                'domain': [('id', 'in', tasks)],
                }



