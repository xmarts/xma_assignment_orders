# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2021-Present Bodegas Alianza - Jose Luigi Tolayo
#     (<>).
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Bodegas Alianza Sincronización',
    'version': '1.0',
    'license': 'Other proprietary',
    'price': 9999.0,
    'category': 'Sales',
    'currency': 'MXN',
    'summary': """Bodegas Alianza Custom module""",
    'description': "",
    'author': 'José Luigi Tolayo Osorio',
    'support': 'luigi.tolayo@bodegasalianza.com',
    'images': [],

    'depends': [
        'base',
        'base_vat',
        'point_of_sale',
        'sale',
        'sale_management',
        'l10n_mx',
        'l10n_mx_edi',
        'stock',
        'stock_landed_costs',
        'web_notify',
        'stock_landed_costs',
        'hr',
        'account_accountant',
        'base_address_extended',
        'contacts',
        'web_map'
    ],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/account_move_view.xml',
        'views/ba_synchronize_view.xml',
        'views/res_company_view.xml',
        'views/res_users_view.xml',
        'views/postal_code_view.xml',
        'views/postal_code_sat_view.xml',
        'views/colonies_sat_view.xml',
        'views/res_city_sat_view.xml',
        'views/res_partner_view.xml',
        'views/product_template_view.xml',
        'views/pos_order_view.xml',
        'views/product_pricelist_view.xml',
        'views/sale_order_view.xml',
        'views/stock_warehouse_view.xml',
        'views/additional_cost_view.xml',
        'views/purchase_order_view.xml',
        'views/stock_move_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_quant_view.xml',
        'views/stock_location_view.xml',
        'views/ir_sequence_view.xml',
        'views/hr_department_view.xml',
        'views/hr_employee_view.xml',
        'views/change_prices_view.xml',
        'views/pos_config_view.xml',
        'views/params_serie_point_sale_warehouse_view.xml',
        'views/params_log_comercial_view.xml',
        'views/imported_pricelist_view.xml',
        'views/barcodes_product_view.xml',
        'views/displacement_level_view.xml',
        'views/sale_delivery_available_ba_view.xml',
        'views/sale_delivery_ba_view.xml',
        #'views/latitude_length_by_cp_view.xml',

        'wizard/views/create_landed_cost_view.xml',
        'wizard/views/create_or_update_pricelist_view.xml',
        'wizard/views/import_update_pricelist_view.xml',


        #'views/uom_category_view.xml',
        #'views/survey_survey_view.xml',

    ],
    'installable': True,
    'application': False,
}


