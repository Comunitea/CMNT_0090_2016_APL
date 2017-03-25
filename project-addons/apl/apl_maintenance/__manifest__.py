# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


{
    'name': 'Modulo APL',
    'version': '10.0',
    'author': 'Comunitea, ',
    "category": "",
    'description': """
        Link equipment with task and projects.
        Users by equipment.
        """,
    'license': 'AGPL-3',
    'depends': [
        'base', 'project', 'maintenance', 'hr', 'hr_holidays'
    ],
    'contributors': [
        "Comunitea",
        "Kiko Sanchez<kiko@comunitea.com>",],
    "data": [
        'views/maintenance.xml',
        'views/project.xml',
        'views/hr.xml'
    ],
    "demo": [

    ],
    'test': [

    ],
    'installable': True
}
