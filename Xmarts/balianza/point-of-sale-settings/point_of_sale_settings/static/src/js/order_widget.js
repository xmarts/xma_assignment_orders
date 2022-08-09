odoo.define('point_of_sale_settings.Order_widget', function(require) {
    'use strict';

    const OrderWidget = require('point_of_sale.OrderWidget');
    const Registries = require('point_of_sale.Registries');

    const PosOrderWidget = OrderWidget =>
        class extends OrderWidget {
            _getSelectedLine() {
                return this.order.get_selected_orderline();
            }
            get _getCountInv() {
                var res = {'countCajInv': 0, 'countUnidInv': 0};
                var linea_selected = this.order.get_selected_orderline();
                var count_product_inv = linea_selected.get_qty_inv_();
                var count_product_x_caja = linea_selected.get_count_product_x_caja();
                if(linea_selected.get_unit_caja() && count_product_x_caja > 1 && count_product_inv >= count_product_x_caja){
                    var cajas = parseInt(count_product_inv/count_product_x_caja);
                    res['countCajInv'] = cajas;
                    var unidades = cajas * count_product_x_caja;
                    if(unidades < count_product_inv){
                        var unidades_libres = count_product_inv - unidades;
                        res['countUnidInv'] = unidades_libres;
                    }
                } else {
                    res['countUnidInv'] = count_product_inv;
                }
                res['totalProductInv'] = count_product_inv;
                return res
            }
            get _getTypeUnitCaja() {
                return this.order.get_selected_orderline().get_unit_caja();
            }
            get _getTypeUnit() {
                return this.order.get_selected_orderline().get_unit();
            }        
        }
    Registries.Component.extend(OrderWidget, PosOrderWidget);

    return OrderWidget;
});
