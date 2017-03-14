# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
import datetime

class Employee(models.Model):

    _inherit = "hr.employee"

    employee_code = fields.Char("Codigo", help ="Codigo de empleado")


class HrHolidays(models.Model):

    _inherit = "hr.holidays"

    remaining_leaves_by_type = fields.Float(compute='_compute_leaves_by_type', string='Remaining Leaves',
                                    help='Maximum Leaves Allowed - Leaves Already Taken')

    number_of_days_formatted = fields.Char(compute="_compute_number_days_formatted")


    @api.multi
    def _compute_leaves_by_type(self):

        self.remaining_leaves_by_type = self.with_context(employee_id=self.employee_id.id).holiday_status_id.remaining_leaves

    @api.multi
    def _compute_number_days_formatted(self):

        duration = self.number_of_days_temp
        days = int(duration)
        hours = (duration - days) * 8
        hour = int(hours)
        minutes = int((hours - hour) * 60)

        if days:
            self.number_of_days_formatted = '%02d dia(s), %02d:%02d' %(days, hours, minutes)
        else:
            self.number_of_days_formatted = '%02d:%02d' %(hours, minutes)

