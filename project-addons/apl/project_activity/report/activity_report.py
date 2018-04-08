# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ReportProjectActivityUser(models.Model):
    _name = "report.project.activity.user"
    _description = "Activities by user and project"
    _order = 'name desc, project_id'
    _auto = False

    name = fields.Char(string='Actividad', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsable', readonly=True)
    date_start = fields.Datetime(string='Fecha de incio', readonly=True)
    no_of_days = fields.Integer(string='# Duración', readonly=True)
    date_end = fields.Datetime(string='Fecha dfin', readonly=True)
    #date_deadline = fields.Date(string='Deadline', readonly=True)
    #date_last_stage_update = fields.Datetime(string='Last Stage Update', readonly=True)
    project_id = fields.Many2one('project.project', string='Proyecto', readonly=True)
    closing_days = fields.Float(string='# Dias para finalizar',
        digits=(16,2), readonly=True, group_operator="avg",
        help="Number of Days to close the activity")
    opening_days = fields.Float(string='# Días desde el inicio',
        digits=(16,2), readonly=True, group_operator="avg",
        help="Number of Days to Open the activity")
    delay_endings_days = fields.Float(string='# Días hasta el fin', digits=(16,2), readonly=True)
    nbr = fields.Integer('# de actividades', readonly=True)  # TDE FIXME master: rename into nbr_tasks

    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    state = fields.Selection([
        ('template', 'Template'),
        ('draft', 'Borrador'),
        ('quoted', 'Presupuestado'),
        ('progress', 'En ejecución'),
        ('done', 'Realizado'),
        ('closed', 'Cerrado'),
        ('not acepted', 'No aceptado')
    ], string="Estado", required=True, readonly=True)
    planned_cost = fields.Float("Coste previsto", help="Suma de los costes estimados de las tareas",
                                readonly=True)
    real_cost = fields.Float("Coste real", multi=True, help="Suma de costes reales de las tareas",
                             readonly=True)
    budget_price = fields.Float("Coste facturable",readonly=True)

    cost_balance = fields.Float("Balance de costes", help="Coste presupuestado menos coste real",
                                readonly=True)


    def _select(self):
        select_str = """
             SELECT
                    (select 1 ) AS nbr,
                    pa.id as id,
                    (select min(date_start) from project_task pt where pt.activity_id = pa.id) as date_start,
                    (select min(date_end) from project_task pt where pt.activity_id = pa.id) as date_end,
                    abs((extract('epoch' from (pa.write_date-date_start)))/(3600*24))  as no_of_days,
                    pa.user_id as user_id,
                    pa.project_id as project_id,
                    pa.planned_cost as planned_cost,
                    pa.real_cost as real_cost,
                    pa.budget_price as budget_price,
                    pa.cost_balance as cost_balance,
                    pa.name as name,
                    pp.state as state,
                    (extract('epoch' from (pa.write_date-pa.create_date)))/(3600*24)  as closing_days,
                    (extract('epoch' from (date_start-pa.create_date)))/(3600*24)  as opening_days,
                    (extract('epoch' from ((select min(date_end) from project_task pt where pt.activity_id = pa.id)-(now() at time zone 'UTC'))))/(3600*24)  as delay_endings_days
                    
        """
        return select_str

    def _group_by(self):
        group_by_str = """
                GROUP BY
                    pa.id,
                    pa.create_date,
                    pa.write_date,
                    date_start,
                    date_end,
                    pa.user_id,
                    pa.project_id,
                    pa.planned_cost,
                    pa.real_cost,
                    pa.budget_price,
                    pa.cost_balance,
                    pa.name,
                    pp.state
        """
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
              %s
              FROM project_activity pa 
              inner join project_project pp on pp.id = pa.project_id
                %s
        """ % (self._table, self._select(), self._group_by()))
