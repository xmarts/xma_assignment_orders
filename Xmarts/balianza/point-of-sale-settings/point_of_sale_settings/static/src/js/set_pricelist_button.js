odoo.define('point_of_sale_settings.Set_pricelist_button', function(require) {
    'use strict';

    const SetPricelistButton = require('point_of_sale.SetPricelistButton');
    const Registries = require('point_of_sale.Registries');

    const PosSetPricelistButton = SetPricelistButton =>
        class extends SetPricelistButton {
            async onClick() {
                console.log("0000000000000000000000000000000000000000000000000 ", this.currentOrder.get_client())
                // if(this.currentOrder.get_client() === null){
                //     console.log("111111111111111111111111111111111111111111111111111111")
                //     // Create the list to be passed to the SelectionPopup.
                //     // Pricelist object is passed as item in the list because it
                //     // is the object that will be returned when the popup is confirmed.
                //     const selectionList = this.env.pos.pricelists.map(pricelist => ({
                //         id: pricelist.id,
                //         label: pricelist.name,
                //         isSelected: pricelist.id === this.currentOrder.pricelist.id,
                //         item: pricelist,
                //     }));

                //     const { confirmed, payload: selectedPricelist } = await this.showPopup(
                //         'SelectionPopup',
                //         {
                //             title: this.env._t('Select the pricelist'),
                //             list: selectionList,
                //         }
                //     );

                //     if (confirmed) {
                //         this.currentOrder.set_pricelist(selectedPricelist);
                //     }
                // } else {
                //     console.log("22222222222222222222222222222222222222222222222222222222222 ", this.currentOrder.get_client())
                // }
            }
        }
    Registries.Component.extend(SetPricelistButton, PosSetPricelistButton);

    return SetPricelistButton;
});