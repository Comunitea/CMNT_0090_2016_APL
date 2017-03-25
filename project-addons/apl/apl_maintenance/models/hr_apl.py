# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import datetime
from datetime import timedelta
from odoo import fields, models, tools, api, _
from odoo import fields as fields2
from odoo.exceptions import UserError, ValidationError

import pytz

class ResourceResource(models.Model):
    _inherit = "resource.resource"

    def is_work_day(self, date):
        return self._is_work_day(date)


class HREmployee(models.Model):

    _inherit = 'hr.employee'

class APLResorceCalendarLeaves(models.Model):

    _inherit = 'resource.calendar.leaves'
    all_day = fields.Boolean("All day", default=True, help="Check for the hole day")

class APLHolidays(models.Model):

    _inherit = 'hr.holidays'
    all_day = fields.Boolean ("All day", default=True, help="Check for the hole day")

    @api.model
    def default_get(self, fields):
        res = super(APLHolidays, self).default_get(fields)
        now = fields2.Datetime.now()
        now_ = fields2.Datetime.from_string(now)
        date_ = now_ - datetime.timedelta(hours=now_.hour, minutes=now_.minute, seconds=now_.second)
        date_from = fields2.Datetime.to_string(date_)
        date_ = date_ + datetime.timedelta(hours=22, minutes=59, seconds=59)

        tz = self.env.user.tz

        date_to = fields2.Datetime.to_string(date_)
        print date_from + ' to ' + date_to
        res['date_from'] = date_from
        res['date_to'] = date_to

        return res
    # @api.multi
    # def _create_resource_leave(self):
    #     """ This method will create entry in resource calendar leave object at the time of holidays validated """
    #     super(APLHolidays, self)._create_resource_leave()
    #     for leave in self:
    #         domain = [('holiday_id', '=', leave.id)]
    #         rcl = self.env['resource.calendar.leaves'].search(domain)
    #         all_day = leave.parent_id.all_day if leave.parent_id else leave.all_day
    #         rcl.all_day = all_day
    #         if all_day:
    #             leave.date_from = leave.date_from.replace(hour=0, minute=0, second=0)
    #             leave.date_to = leave.date_to.replace(hour=23, minute=59, second=59)
    #     return True
    #
    #
    # @api.model
    # def create(self, vals):
    #     return super(APLHolidays, self).write(vals)

    @api.multi
    def write(self, vals):

        if 'all_day' in vals.keys():
            raise ValidationError ("No puedes cambiar esto una vez creada la solicitud")
        return super(APLHolidays, self).write(vals)
