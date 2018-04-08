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

class APLResorceCalendarLeaves(models.Model):

    _inherit = 'resource.calendar.leaves'

    all_day = fields.Boolean("All day", default=True, help="Check for the hole day")

class APLHolidays(models.Model):

    _inherit = 'hr.holidays'

    all_day = fields.Boolean ("All day", default=True, readonly=True, help="Check for the hole day",  states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

