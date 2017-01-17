# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools

# vecesito heredar esto tambien de hr_timesheet
class ReportProjectActivityTaskUser(models.Model):

    _inherit = "report.project.task.user"

    activity_id = fields.Many2one("project.activity", readonly=True)
    real_cost = fields.Float('Cost', group_operator='sum', readonly=True)
    planned_cost = fields.Float('Planned Cost', group_operator='sum', readonly=True)


    def _select(self):
        return super(ReportProjectActivityTaskUser, self)._select() + """,
            activity_id as activity_id,
            real_cost as real_cost,
            planned_cost as planned_cost
            """

    def _group_by(self):
        return super(ReportProjectActivityTaskUser, self)._group_by() + """,
            activity_id,
            real_cost,
            planned_cost
            """