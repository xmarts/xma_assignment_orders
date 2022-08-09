odoo.define('point_of_sale_settings.Client_list_screen', function(require) {

    const ClientListScreen = require('point_of_sale.ClientListScreen');
    const Registries = require('point_of_sale.Registries');
    const { isRpcError } = require('point_of_sale.utils');

    const PosClientListScreen = ClientListScreen =>
        class extends ClientListScreen {
            async saveChanges(event) {
                console.log("11111111111 14")
                try {
                    let partnerId = await this.rpc({
                        model: 'res.partner',
                        method: 'create_from_ui',
                        args: [event.detail.processedChanges],
                    });
                    if(partnerId === 'ExisteRFC'){
                        this.showPopup('ErrorPopup', {
                            title: this.env._t(
                                'Ya existe un cliente con ese RFC.'
                            ),
                        });
                    } else {
                        await this.env.pos.load_new_partners();
                        this.state.selectedClient = this.env.pos.db.get_partner_by_id(partnerId);
                        var cliente = this.env.pos.get_order().get_client()
                        if(cliente){
                            if(cliente.id === this.state.selectedClient.id){
                                console.log("rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr 1 ", this.env.pos.pricelists)
                                var lista = _.findWhere(this.env.pos.pricelists, {
                                    id: this.state.selectedClient.property_product_pricelist[0],
                                })
                                console.log("rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr 1.1 ", lista)
                                console.log("rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr 1.1.1 ", this.state.selectedClient.property_product_pricelist[0])
                                if(lista){
                                    this.env.pos.get_order().set_pricelist(lista);
                                }
                            }
                        }
                        console.log("rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr 2 ", this.state.selectedClient)
                        this.state.detailIsShown = false;
                        this.render();
                    }
                } catch (error) {
                    if (isRpcError(error) && error.message.code < 0) {
                        await this.showPopup('OfflineErrorPopup', {
                            title: this.env._t('Offline'),
                            body: this.env._t('Unable to save changes.'),
                        });
                    } else {
                        throw error;
                    }
                }
            }
            // funcion del POS selecciona un cliente para cada pedido
            clickNext() {
                if(this.props.repart === 'True'){
                    this.state.selectedClient = this.nextButton.command === 'set' ? this.state.selectedClient : null;
                    this.confirm();
                } else {
                    if(this.env.pos.get_order().get_tipo_compra()){
                        this.state.selectedClient = this.nextButton.command === 'set' ? this.state.selectedClient : null;
                        this.confirm();
                    } else{
                        this.showPopup('ErrorPopup', {
                            body: this.env._t(
                                'Es necesario seleccionar el Tipo de Compra.'
                            ),
                        });
                    }
                }
            }
        };

    Registries.Component.extend(ClientListScreen, PosClientListScreen);

    return ClientListScreen;
});
