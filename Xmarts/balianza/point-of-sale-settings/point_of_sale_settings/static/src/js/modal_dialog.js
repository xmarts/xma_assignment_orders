odoo.define('point_of_sale.ModalDialog', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');

    // formerly ModalDialogWidget
    class ModalDialog extends ErrorPopup {}
    ModalDialog.template = 'ModalDialog';
    ModalDialog.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: '¡WARNING!',
        body: '',
    };

    Registries.Component.add(ModalDialog);

    return ModalDialog;
});