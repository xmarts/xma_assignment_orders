odoo.define('point_of_sale_settings.Numpad_widget', function(require) {

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const PosNumpadWidget = NumpadWidget =>
        class extends NumpadWidget {
            constructor() {
                super(...arguments);
                this.lineas = {}
            }
            get currentOrder() {
                return this.env.pos.get_order();
            }
            async set_tipo_compra(obj) {
                var dic = null
                if(obj){
                    console.log("yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy ", obj.id)
                    dic = this.currentOrder.get_serie_bd(obj.id)
                } else {
                    this.currentOrder.set_client(null)
                }
                this.currentOrder.set_tipo_compra(dic);
            }
            async clicked_add_tipo_compra() {
                this.currentOrder.load_series()
                var tipo_compra = null
                if(this.currentOrder.get_tipo_compra()){
                    tipo_compra = this.currentOrder.get_tipo_compra().indice
                }
                let selectionList = [{
                    id: null,
                    label:'---Seleccione el tipo de compra---',
                    isSelected: null === tipo_compra,
                    item: {id:null, data:'----Seleccione el tipo de compra----'},
                }];
                const sweetArray = [{
                    id: 0,
                    data: 'MY',
                },{
                    id: 1,
                    data: 'MN',
                }]
                let subs = sweetArray.map(category => ({
                    id: category['id'],
                    label: category['data'],
                    isSelected: category['id'] === tipo_compra,
                    item: category,
                }));
                selectionList = selectionList.concat(subs);
                const { confirmed, payload: selectedCategory } = await this.showPopup(
                    'SelectionPopup',
                    {
                        title: this.env._t('Tipos de compra'),
                        list: selectionList,
                    }
                );
                if (confirmed) {
                    console.log("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz ", sweetArray[selectedCategory.id])
                    this.set_tipo_compra(sweetArray[selectedCategory.id]);
                }
            }
            // Funcion nativa del POS
            async changeMode(mode) {
                if(this.currentOrder.get_selected_orderline() !== undefined){
                    var line_select = this.currentOrder.get_selected_orderline()
                    var product_id = this.currentOrder.get_selected_orderline().get_product().id
                    if(this.lineas[product_id]){
                        this.lineas[product_id].count = ''
                    }
                    await super.changeMode(mode);
                    if(mode === 'quantity'){
                        const { confirmed, payload } = await this.showPopup('NumberPopup', {
                           title: this.env._t('Ingrese una cantidad'),
                           body: this.env._t('This click is successfully done.'),
                        });
                        if(confirmed){
                            if (Math.sign(payload) === 0) {
                                line_select.set_quantity(0)
                                return;
                            } else if(Math.sign(payload) === -1 || Math.sign(payload) === -0) {
                                this.showPopup('ModalDialog', {
                                    body: this.env._t(
                                        'La cantidad ingresada es incorrecta, no se aceptan cantidades negativas.'
                                    ),
                                });
                                return;
                            } else if((payload % 1 === 0) === false) {
                                this.showPopup('ModalDialog', {
                                    body: this.env._t(
                                        'La cantidad ingresada es incorrecta, no se aceptan decimales.'
                                    ),
                                });
                                return;
                            }
                            if(this.validExistInv(payload, line_select)){
                                var count_product_x_caja = line_select.get_count_product_x_caja()
                                if(line_select.get_unit_caja() && count_product_x_caja > 1 && payload >= count_product_x_caja){
                                    line_select.set_quantity(0)
                                    var cajas = parseInt(payload/count_product_x_caja);
                                    line_select.set_qty_caja(cajas)
                                    var unidades = cajas * count_product_x_caja;
                                    if(unidades < payload){
                                        var unidades_libres = payload - unidades;
                                        line_select.set_quantity(unidades_libres)
                                    }
                                } else {
                                    line_select.set_quantity(payload)
                                }
                                NumberBuffer.reset();
                                return;
                            }
                        }
                    } else if(mode === 'quantity_caja') {
                        if(this.validPorCaja()){
                            this.corroborFields(line_select)
                            var quantity = line_select.get_quantity()
                            var total_quantity_x_cajas = line_select.get_total_quantity_x_cajas()
                            var total_products = quantity + total_quantity_x_cajas
                            this.validExistInv(total_products, line_select)
                        }
                    }
                } else {
                    await super.changeMode(mode);
                }
            }
            sendInput(key) {
                if(this.currentOrder.get_selected_orderline() !== undefined){
                    var line_select = this.currentOrder.get_selected_orderline()
                    if(key !== 'Backspace'){                    
                        if(this.props.activeMode === 'quantity_caja'){
                            if(this.validPorCaja()){
                                this.corroborFields(line_select)
                                var quantity = line_select.get_quantity()
                                var total_quantity_x_cajas = line_select.get_total_quantity_x_cajas()
                                var total_products = quantity + total_quantity_x_cajas
                                if(!this.validExistInv(total_products, line_select)){
                                    return;
                                }
                                var product_id = this.currentOrder.get_selected_orderline().get_product().id
                                if(!this.lineas[product_id]){
                                    this.lineas[product_id] = {count: ''}
                                }
                                var count_product_x_caja = line_select.get_count_product_x_caja()
                                var cant_cajas = parseInt(this.lineas[product_id].count + key)
                                var cant_products_total = cant_cajas * count_product_x_caja
                                if(this.validExistInv(cant_products_total, line_select)){
                                    this.lineas[product_id].count = this.lineas[product_id].count + key
                                    line_select.set_qty_caja(cant_cajas)
                                }
                            }
                        }
                    } else if(key === 'Backspace'){
                        var product_id = this.currentOrder.get_selected_orderline().get_product().id
                        if(this.props.activeMode === 'quantity_caja'){
                            if(line_select.get_qty_caja() > 0){
                                if(product_id in this.lineas){
                                    if(this.lineas[product_id].count > 0){
                                        this.lineas[product_id].count = ''
                                    }
                                }
                                line_select.set_qty_caja(0)
                                return;
                            }
                        } else if(this.props.activeMode === 'quantity'){
                            if(line_select.get_quantity() > 0){
                                line_select.set_quantity(0)
                                return;
                            }
                        }
                        if(line_select.get_quantity() === 0 && line_select.get_qty_caja() === 0){
                            this.currentOrder.remove_orderline(this.currentOrder.get_selected_orderline())
                        }
                    }
                }
            }
            corroborFields(line_select) {
                var quantity = line_select.get_quantity()
                // var total_quantity_x_cajas = line_select.get_total_quantity_x_cajas()
                var count_product_x_caja = line_select.get_count_product_x_caja()
                if(line_select.get_unit_caja() && count_product_x_caja > 1 && line_select.get_qty_caja() > 0 && quantity >= count_product_x_caja){
                    line_select.set_quantity(0)
                    // quantity = line_select.get_quantity()
                    // total_products = quantity + total_quantity_x_cajas
                }

            }
            validPorCaja() {
                if(this.currentOrder.get_selected_orderline() !== undefined){
                    var line_select = this.currentOrder.get_selected_orderline()
                    var count_product_x_caja = line_select.get_count_product_x_caja()
                    if(!line_select.get_unit_caja() || count_product_x_caja <= 1){
                        this.showPopup('ModalDialog', {
                            body: this.env._t(
                                'El producto: '+line_select.get_product().display_name.toString()+' solo se puede vender por '+line_select.get_unit().name.toString()+'.'
                            ),
                        });
                        return false;
                    }
                    return true;
                }
            }
            validExistInv(total_products, line_select) {
                var count_unid_inv = line_select.get_count_unidades_inv()
                var count_product_x_caja = line_select.get_count_product_x_caja()
                if(total_products > count_unid_inv){
                    var count_product = 0
                    var cajas = 0
                    count_unid_inv = line_select.get_qty_inv_()
                    if(line_select.get_unit_caja() && count_product_x_caja > 1 && count_unid_inv >= count_product_x_caja){
                        cajas = parseInt(count_unid_inv/count_product_x_caja);
                        var unidades = cajas * count_product_x_caja;
                        if(unidades < count_unid_inv){
                            var unidades_libres = count_unid_inv - unidades;
                            count_product = unidades_libres;
                        }
                    } else {
                        count_product = count_unid_inv
                    }
                    var cadena = ''
                    if(!line_select.get_unit_caja() || count_product_x_caja <= 1){
                        cadena = count_unid_inv.toString()+' '+line_select.get_unit().name.toString()+'.'
                    } else {
                        cadena = cajas.toString()+' '+line_select.get_unit_caja().name.toString()+' con '+count_product.toString()+' '+line_select.get_unit().name.toString()+', total: '+count_unid_inv.toString()+' '+line_select.get_unit().name.toString()+'.'
                    }
                    this.showPopup('ModalDialog', {
                        body: this.env._t(
                            'No existe disponibilidad del producto suficientes en el inventario, existen '+cadena
                        ),
                    });
                    return false;
                }
                return true;
            }
            // Funcion nativa del POS
            // sendInput1(key) {
            //     NumberBuffer.use({
            //         nonKeyboardInputEvent: 'numpad-click-input',
            //         triggerAtInput: 'update-selected-orderline',
            //         useWithBarcode: true,
            //     });
            //     this.trigger('numpad-click-input', { key });
            //     NumberBuffer.capture();
            //     if(this.currentOrder.get_selected_orderline() !== undefined){
            //         var line_select = this.currentOrder.get_selected_orderline()
            //         var quantity = line_select.get_quantity()
            //         var total_quantity_x_cajas = line_select.get_total_quantity_x_cajas()
            //         var total_products = quantity + total_quantity_x_cajas
            //         if(key !== 'Backspace'){
            //             var count_product_x_caja = line_select.get_count_product_x_caja()
            //             if(this.props.activeMode === 'quantity_caja'){
            //                 if(line_select.get_unit_caja() && count_product_x_caja > 1 && line_select.get_qty_caja() > 0 && quantity >= count_product_x_caja){
            //                     line_select.set_quantity(0)
            //                     quantity = line_select.get_quantity()
            //                     total_products = quantity + total_quantity_x_cajas
            //                 }
            //                 if(!line_select.get_unit_caja() || count_product_x_caja <= 1){
            //                     key = 'Backspace'
            //                     this.trigger('numpad-click-input', { key });
            //                     this.showPopup('ModalDialog', {
            //                         body: this.env._t(
            //                             'El producto: '+line_select.get_product().display_name.toString()+' solo se puede vender por '+line_select.get_unit().name.toString()+'.'
            //                         ),
            //                     });
            //                     return;
            //                 }
            //             }
            //             var count_unid_inv = line_select.get_count_unidades_inv()
            //             if(line_select.get_unit_caja() && count_product_x_caja > 1 && quantity >= count_product_x_caja && total_products <= count_unid_inv){
            //                 key = 'Backspace'
            //                 this.trigger('numpad-click-input', { key });
            //                 return;
            //             }
            //             if(total_products > count_unid_inv){
            //                 key = 'Backspace'
            //                 this.trigger('numpad-click-input', { key });
            //                 NumberBuffer.capture();
            //                 var count_product = 0
            //                 var cajas = 0
            //                 count_unid_inv = line_select.get_qty_inv_()
            //                 if(line_select.get_unit_caja() && count_product_x_caja > 1 && count_unid_inv >= count_product_x_caja){
            //                     cajas = parseInt(count_unid_inv/count_product_x_caja);
            //                     var unidades = cajas * count_product_x_caja;
            //                     if(unidades < count_unid_inv){
            //                         var unidades_libres = count_unid_inv - unidades;
            //                         count_product = unidades_libres;
            //                     }
            //                 } else {
            //                     count_product = count_unid_inv
            //                 }
            //                 var cadena = ''
            //                 if(!line_select.get_unit_caja() || count_product_x_caja <= 1){
            //                     cadena = count_unid_inv.toString()+' '+line_select.get_unit().name.toString()+'.'
            //                 } else {
            //                     cadena = cajas.toString()+' '+line_select.get_unit_caja().name.toString()+' con '+count_product.toString()+' '+line_select.get_unit().name.toString()+', total: '+count_unid_inv.toString()+' '+line_select.get_unit().name.toString()+'.'
            //                 }
            //                 this.showPopup('ModalDialog', {
            //                     body: this.env._t(
            //                         'No existe disponibilidad del producto suficientes en el inventario, existen '+cadena
            //                     ),
            //                 });
            //                 return;
            //             }
            //         }
            //         line_select.set_qty_inv(total_products)
            //     }
            // }
        };

    Registries.Component.extend(NumpadWidget, PosNumpadWidget);

    return NumpadWidget;
});
