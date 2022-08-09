odoo.define('point_of_sale_settings.inher_product_screen', function(require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');

    const PosProductScreen = ProductScreen =>
        class extends ProductScreen {
            async _clickProduct(event) {
                if (!this.currentOrder) {
                    this.env.pos.add_new_order();
                }
                const product = event.detail;
                const options = await this._getAddProductOptions(product);
                // Do not add product if options is undefined.
                if (!options) return;
                if(product.scan_in_pos){
                    this.showPopup('ErrorPopup', {
                        body: this.env._t(
                            'Es necesario escanear con el código de barra.'
                        ),
                    });
                    return;
                }
                if(!this.currentOrder.get_client()){
                    this.showPopup('ErrorPopup', {
                        body: this.env._t(
                            'Es necesario seleccionar un cliente, para poder agregar un producto.'
                        ),
                    });
                    return;
                }
                if(product.get_count_unidades_inv() === 0){
                    this.showPopup('ModalDialog', {
                        body: this.env._t(
                            'No existe disponibilidad del producto en el inventario, existen 0 unidades.'
                        ),
                    });
                    return;
                }
                // Add the product after having the extra information.
                options['quantity'] = 0
                this.currentOrder.add_product(product, options);
                NumberBuffer.reset();
            }
            _setValue(val) {
                if (this.currentOrder.get_selected_orderline()) {
                    if (this.state.numpadMode === 'quantity') {
                        this.currentOrder.get_selected_orderline().set_quantity(val);
                    } else if (this.state.numpadMode === 'quantity_caja') {
                        this.currentOrder.get_selected_orderline().set_qty_caja(val);
                    } else if (this.state.numpadMode === 'discount') {
                        this.currentOrder.get_selected_orderline().set_discount(val);
                    } else if (this.state.numpadMode === 'price') {
                        var selected_orderline = this.currentOrder.get_selected_orderline();
                        selected_orderline.price_manually_set = true;
                        selected_orderline.set_unit_price(val);
                    }
                    if (this.env.pos.config.iface_customer_facing_display) {
                        this.env.pos.send_current_order_to_customer_facing_display();
                    }
                }
            }
            async _barcodeProductAction(code) {
                const result = await this.rpc({
                    model: 'product.template',
                    method: 'search_barcode',
                    args: [code.base_code],
                });
                const product = this.env.pos.db.get_product_by_id(result.product_id)
                if (!product) {
                    return this._barcodeErrorAction(code);
                }
                var quantity = 0
                var qty_caja = 0
                if(result.res){
                    var unidad_medida = parseInt(result.uom_id)
                    if(unidad_medida === parseInt(product.uom_id[0])){
                        quantity = 1
                    } else if(unidad_medida === parseInt(product.sub_type_uom[0])){
                        if(parseInt(product.sub_type_uom[0]) && parseInt(product.quantity_uom) > 1){
                            qty_caja = 1
                        } else{
                            return this.showPopup('ModalDialog', {
                                body: this.env._t(
                                    'El producto: '+product.display_name+' solo se puede vender por '+product.uom_id[1]+'.'
                                ),
                            });
                        }
                    } else{
                        return this.showPopup('ModalDialog', {
                            body: this.env._t(
                                'El producto '+product.display_name+', no tiene seleccionada una Unidad de medida o Sub-unidad de medida con el nombre '+result.uom_name+'.'
                                // 'No esta seleccionada una Unidad de medida o Sub-unidad de medida en el producto '+product.display_name+', para '+result.uom_name+'.'
                                // 'No coincide la unidad de medida del codigo de barras con el que se tiene en el producto '+product.display_name+', verifique recargando la pagina o comuniquese con el administrador.'
                            ),
                        });
                    }
                } else{
                    return this._barcodeErrorAction(code);
                }
                const options = await this._getAddProductOptions(product);
                // Do not proceed on adding the product when no options is returned.
                // This is consistent with _clickProduct.
                if (!options) return;

                // update the options depending on the type of the scanned code
                if (code.type === 'price') {
                    Object.assign(options, {
                        price: code.value,
                        extras: {
                            price_manually_set: true,
                        },
                    });
                } else if (code.type === 'weight') {
                    Object.assign(options, {
                        quantity: code.value,
                        merge: false,
                    });
                } else if (code.type === 'discount') {
                    Object.assign(options, {
                        discount: code.value,
                        merge: false,
                    });
                }
                options['quantity'] = 0
                options['qty_caja'] = 0
                if(quantity > 0){
                    options['quantity'] = 1
                }
                if(qty_caja > 0){
                    options['qty_caja'] = 1
                }
                this.currentOrder.add_product(product,  options)
            }
        };
    Registries.Component.extend(ProductScreen, PosProductScreen);
    return ProductScreen;
});
