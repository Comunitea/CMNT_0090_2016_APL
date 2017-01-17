# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields


class ProjectActivityTemplateWz(models.TransientModel):

    _name = 'project.activity.template.wz'

    @api.model
    def _get_default_activity(self):
        return self._context['active_id']

    @api.model
    def _get_default_name(self):
        id = self._context['active_id']

        return self.env['project.activity'].browse(id).name

    default_activity = fields.Many2one('project.activity', string="Actividad a duplicar", default=_get_default_activity)
    new_name = fields.Char("Name", default=_get_default_name)
    copy_planned_cost = fields.Boolean('Costes en la plantilla', default= True)
    copy_user_id = fields.Boolean('Responsable', default= True)
    copy_equipo = fields.Boolean('Equipo', default= True)

    @api.multi
    def create_activity_template(self):
        vals = {'is_template': True,
                'name': self.new_name,
                'project_id': False
                }
        contextual_self = self.with_context(default_project_id=False)
        new_activity = contextual_self.default_activity.copy(vals)
        new_activity.project_id = False
        return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'project.activity',
                        'view_mode': 'form',
                        'res_id': new_activity.id
                        }


    @api.onchange('default_activity')
    def onchange_activity(self):
        self.name= self.default_activity.name


