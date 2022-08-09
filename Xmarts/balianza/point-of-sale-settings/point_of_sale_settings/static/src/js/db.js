odoo.define('point_of_sale_settings._db', function (require) {
    'use strict';

    const PosDB = require('point_of_sale.DB');
    PosDB.include({
        save_series: function(lista_series){
            this.load('series',[]);
            this.remove_all_series();
            this.save('series',lista_series);
        },
        get_series: function(){
            return this.load('series',[]);
        },
        remove_all_series: function(){
            this.save('series',[]);
        },
        _partner_search_string: function(partner){
            var str =  partner.name || '';
            if(partner.barcode){
                str += '|' + partner.barcode;
            }
            if(partner.address){
                str += '|' + partner.address;
            }
            if(partner.phone){
                str += '|' + partner.phone.split(' ').join('');
            }
            if(partner.mobile){
                str += '|' + partner.mobile.split(' ').join('');
            }
            if(partner.email){
                str += '|' + partner.email;
            }
            if(partner.vat){
                str += '|' + partner.vat;
            }
            if(partner.ref){
                str += '|' + partner.ref;
            }
            str = '' + partner.id + ':' + str.replace(':', '').replace(/\n/g, ' ') + '\n';
            return str;
        },
    });
});