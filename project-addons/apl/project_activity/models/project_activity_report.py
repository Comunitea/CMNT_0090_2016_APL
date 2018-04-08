# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools

# vecesito heredar esto tambien de hr_timesheet
class ReportProjectActivityTaskUser(models.Model):

    _inherit = "report.project.task.user"


    activity_id = fields.Many2one("project.activity", readonly=True)
    new_activity_created = fields.Many2one("project.activity", 'Solicitud', group_operator='avg', readonly=True)
    real_cost = fields.Float('Cost', group_operator='sum', readonly=True)
    planned_cost = fields.Float('Planned Cost', group_operator='sum', readonly=True)
    tags = fields.Char('Tags', readonly=True)
    activity_real_cost = fields.Float("Coste real de la actividad", group_operator="avg", readonly=True)
    activity_planned_cost = fields.Float("Coste previsto de la actividad", group_operator="avg", readonly=True)
    activity_budget_price = fields.Float("Coste facturable de la actividad", group_operator="avg", readonly=True)

    def _select(self):
        return super(ReportProjectActivityTaskUser, self)._select() + """,
            t.activity_id as activity_id,
            t.new_activity_created as new_activity_created,
            t.task_real_cost as real_cost,
            t.task_planned_cost as planned_cost,
            pa.real_cost as activity_real_cost,
            pa.planned_cost as activity_planned_cost,
            pa.budget_price as activity_budget_price, 
            (select string_agg(pt.name,' ') from project_tags pt
	        inner join project_tags_project_task_rel ptptr on pt.id = ptptr.project_tags_id
	        where ptptr.project_task_id = t.id) as tags 
            """

    def _group_by(self):
        return super(ReportProjectActivityTaskUser, self)._group_by() + """,
            t.activity_id,
            t.task_real_cost,
            t.task_planned_cost,
            t.new_activity_created,
            tags,
            pa.planned_cost,
            pa.budget_price,
            pa.real_cost
            """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        _group = self._group_by().replace('create_date', 't.create_date').replace('write_date', 't.write_date').replace('name', 't.name').replace('stage_id', 't.stage_id')
        self._cr.execute("""
            CREATE view %s as
              %s
              FROM project_task t
              inner join project_activity pa on pa.id = t.activity_id
            WHERE t.active = 'true'
                %s
        """ % (self._table, self._select(), _group))