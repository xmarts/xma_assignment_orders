odoo.define('point_of_sale_settings.Client_details_edit', function(require) {

    const { _t } = require('web.core');
    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');
    const Registries = require('point_of_sale.Registries');

    const PosClientDetailsEdit = ClientDetailsEdit =>
        class extends ClientDetailsEdit {
            saveChanges() {
                let processedChanges = {};
                processedChanges['customer_rank'] = 1;
                processedChanges['customer_created_by'] = 'cliente_creado_pdv';
                for (let [key, value] of Object.entries(this.changes)) {
                    if (this.intFields.includes(key)) {
                        processedChanges[key] = parseInt(value) || false;
                    } else {
                        processedChanges[key] = value;
                    }
                }
                if ((!this.props.partner.name && !processedChanges.name) ||
                    processedChanges.name === '' ){
                    return this.showPopup('ErrorPopup', {
                      title: _t('A Customer Name Is Required'),
                    });
                }
                processedChanges.id = this.props.partner.id || false;
                this.trigger('save-changes', { processedChanges });
            }
        };

    Registries.Component.extend(ClientDetailsEdit, PosClientDetailsEdit);

    return ClientDetailsEdit;
});