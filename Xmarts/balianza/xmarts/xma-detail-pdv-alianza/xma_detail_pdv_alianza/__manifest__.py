# -*- coding: utf-8 -*-
{
    'name': "Detalle PDV",
    'summary': """""",
    'description': """Detalle de datos del PDV:
        Horario de servicio\n
        Disponibilidad\n
        Ubicación\n
        Clasificación de PDV que tiene el servicio delivery disponible\n
        Personal habilitado para delivery""",
    'author': "Xmarts",
    'contributors': "javier.hilario@xmarts.com",
    'website': "http://www.xmarts.com",
    'category': 'Uncategorized',
    'version': '14.0.1.0.0',
    'depends': [
        'base',
        'point_of_sale',
        'hr_attendance',
        'contacts',
        'hr',
        'resource',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/inherit_res_partner_views.xml',
        'views/post_festive_days_views.xml',
        'views/inherit_hr_employee_views.xml',
        'views/inherit_pos_config_views.xml',
        'data/non_working_pdv_cron.xml',
    ],
}
