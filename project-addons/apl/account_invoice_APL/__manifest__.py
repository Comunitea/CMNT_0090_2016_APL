# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnologicos (<http://www.comunitea.com>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


{
    'name': 'Modulo APL Account Invoice',
    'version': '10.0',
    'author': 'Comunitea, ',
    "category": "",
    'license': 'AGPL-3',
    'description': 'Modulo con cambios necesarios para integrar proyectos en facturas',
    'depends': [
        'base', 'account', 'project','l10n_es_account_invoice_sequence'
    ],
    'contributors': [
        "Comunitea",
        "Kiko Sanchez<kiko@comunitea.com>",    ],
    "data": [
        'views/account_invoice.xml',
        'views/project_management.xml'
    ],
    "demo": [

    ],
    'test': [

    ],
    'installable': True
}
