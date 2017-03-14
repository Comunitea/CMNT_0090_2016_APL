# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


{
    'name': 'Modulo APL HR',
    'version': '10.0',
    'author': 'Comunitea, ',
    "category": "",
    'license': 'AGPL-3',
    'description': 'Modulo con cambios necesarios para integraciond e hr_employee',
    'depends': [
        'base', 'hr', 'hr_holidays'
    ],
    'contributors': [
        "Comunitea",
        "Kiko Sanchez<kiko@comunitea.com>",    ],
    "data": [
        'views/hr_employee.xml',
        'report/solicitud_ausencia_report.xml'

    ],


    "demo": [

    ],
    'test': [

    ],
    'installable': True
}
