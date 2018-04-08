# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class Employee(models.Model):

    _inherit = "hr.employee"

    employee_code = fields.Char("Codigo", help ="Codigo de empleado")


class HrHolidays(models.Model):

    _inherit = "hr.holidays"

    @api.model
    def _get_default_date_from(self):
        return fields.Date.today() + ' 06:00:00'



    remaining_leaves_by_type = fields.Float(compute='_compute_leaves_by_type', string='Remaining Leaves',
                                    help='Maximum Leaves Allowed - Leaves Already Taken')

    number_of_days_formatted = fields.Char(compute="_compute_number_days_formatted")
    date_from = fields.Datetime(default=_get_default_date_from)

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for holiday in self:
            domain = [
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>=', holiday.date_from),
                ('type', '=', 'remove'),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(_('You can not have 2 leaves that overlaps on same day!'))

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

    @api.model
    def default_get(self, fields):

        res = super(HrHolidays, self).default_get(fields)
        return res