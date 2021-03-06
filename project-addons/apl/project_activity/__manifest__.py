# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


{
    'name': 'Modulo APL',
    'version': '10.0',
    'author': 'Comunitea, ',
    "category": "",
    'license': 'AGPL-3',
    'depends': [
        'base', 'project'
    ],
    'contributors': [
        "Comunitea",
        "Kiko Sanchez<kiko@comunitea.com>",    ],
    "data": [
        'views/report_activity.xml',
        'views/project_activity.xml',
        'wizard/project_activity_templates.xml',
        'data/project_activity_sequence.xml',
        'report/task_report.xml',
        'report/activity_report.xml',
        'security/ir.model.access.csv',
    ],
    "demo": [

    ],
    'test': [

    ],
    'installable': True
}
