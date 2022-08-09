odoo.define('point_of_sale_settings.Ticket_screen', function(require) {

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');

    const PosTicketScreen = TicketScreen =>
        class extends TicketScreen {
            // funcion nueva para el campo nuevo de serie sobre las lineas del pedido
            getTipoCompra(order) {
                return order.get_tipo_compra_name();
            }
        };

    Registries.Component.extend(TicketScreen, PosTicketScreen);

    return TicketScreen;
});