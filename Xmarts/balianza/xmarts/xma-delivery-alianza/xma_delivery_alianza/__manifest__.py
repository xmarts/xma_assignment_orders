# -*- coding: utf-8 -*-
{
    'name': "Delivery Alianza-ERP",

    'description': """
        Este módulo contiene:
            -Código de acceso del repartidor 
            -Sincronización de datos a la App
            -Seguimiento de ruta de repartidores
            -Registro de cancelación de pedidos 
    """,

    'author': "Xmarts",
    'website': "http://www.erp.xmarts.com",
    'category': 'Delivery',
    'version': '14.0',
    'depends': [
        'base',
        'hr',
        'sale',
        'point_of_sale',
        'survey',
        'account',
        'web',
        'base_geolocalize',
        'xma_detail_pdv_alianza',
    ],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/ir_cron.xml',
        'views/hr_employee_inherit.xml',
        'views/pos_order_inherit.xml',
        'views/sale_order_inherit.xml',
        'views/cancelattions_motives.xml',
        'views/survey_survey_inherit.xml',
        'reports/report_pos_order_alianza.xml',
        'reports/report_account_move_alianza.xml',
        'reports/pos_order_layout.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
