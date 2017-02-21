# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# Kiko Sanchez (<kiko@comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models, tools, api, _

from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class IrSequences(models.Model):

    _inherit = 'ir.sequence'



    def reset_to_number(self, sequence_name = '', next_number = 0):
        domain = [('name','=',sequence_name)]
        sequence = self.env['ir.sequence'].search(domain, limit=1)
        if sequence:
            print "   >>> Reset de %s" % sequence.name
            res = sequence.write({'number_next': next_number})









