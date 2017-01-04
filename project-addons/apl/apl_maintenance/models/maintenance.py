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

class ProjectTask(models.Model):

    _inherit ="project.task"


    @api.one
    def _get_ok_calendar(self):

        if not (self.equipment_id and self.date_start):
            self.ok_calendar = True
            return

        sql = "select count(id) from project_task where ((equipment_id = %s) and ('%s' between date_start and date_end))"%(self.equipment_id and self.equipment_id.id, self.date_start)
        self._cr.execute(sql)

        resw = self._cr.fetchone()
        if resw:
            self.ok_calendar = False
        else:
            self.ok_calendar = True


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

    @api.onchange('equipment_id')
    def get_user_ids_domain(self):

        if self.equipment_id:
            x = {'domain': {'user_ids': [('id', 'in', [x.id for x in self.allowed_user_ids])]}}
        else:
            x = {'domain': {'user_ids': []}}
        return x

    @api.one
    def open_concurrent(self):
        ids = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        domain = [('id', 'in', ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'open.concurring.tasks',
            'res_model': 'product.task',
            'view_type': 'tree',
            'view_mode': 'tree,form',
            'view_id': self.env['ir.ui.view'].search([('name','=','project.task.tree.concurring_tasks')]).id,
            'target': 'current',
            'domain': domain,
        }

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