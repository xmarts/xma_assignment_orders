odoo.define('point_of_sale_settings.Payment_screen', function(require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosPaymentScreen = PaymentScreen =>
        class extends PaymentScreen {
            async selectRepart() {
                const currentRepart = this.currentOrder.get_repart();
                const { confirmed, payload: newRepart } = await this.showTempScreen(
                    'ClientListScreen',
                    { client: currentRepart, repart: 'True'}
                );
                if (confirmed) {
                    this.currentOrder.set_repart(newRepart);
                }
            }
            // funcion nativa editar para agregar restrinccion para que no deje
            // crear un pedido, primero se deve seleccionar el cliente de forma obligatoria.
            async validateOrder(isForceValidate) {
                console.log("ordennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn 0")
                if(this.env.pos.config.cash_rounding) {
                    if(!this.env.pos.get_order().check_paymentlines_rounding()) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Rounding error in payment lines'),
                            body: this.env._t("The amount of your payment lines must be rounded to validate the transaction."),
                        });
                        return;
                    }
                }
                console.log("ordennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn 1 ", this.currentOrder.get_client())
                if(this.currentOrder.get_client()){
                    console.log("ordennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn 2")
                    if(this.currentOrder.get_tipo_compra()){
                        console.log("ordennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn 3")
                        if (await this._isOrderValid(isForceValidate)) {
                            for (let line of this.paymentLines) {
                                if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                            }
                            await this._finalizeValidation();
                        }
                    } else {
                        this.showPopup('ErrorPopup', {
                            body: this.env._t(
                                'Es necesario seleccionar el tipo de compra para poder crear la orden.'
                            ),
                        });
                    }
                } else {
                    this.showPopup('ErrorPopup', {
                        body: this.env._t(
                            'Es necesario seleccionar un cliente para poder crear la orden.'
                        ),
                    });
                }
            }
        };
    Registries.Component.extend(PaymentScreen, PosPaymentScreen);
    return PaymentScreen;
});
