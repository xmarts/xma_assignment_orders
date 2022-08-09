odoo.define('point_of_sale_settings.models', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
const { Gui } = require('point_of_sale.Gui');

var BarcodeParser = require('barcodes.BarcodeParser');
var models = require('point_of_sale.models');
var field_utils = require('web.field_utils');
var utils = require('web.utils');
const NumberBuffer = require('point_of_sale.NumberBuffer');
var round_di = utils.round_decimals;
var round_pr = utils.round_precision;

var _super_pos_model = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    models: [
    {
        label:  'version',
        loaded: function (self) {
            return self.session.rpc('/web/webclient/version_info',{}).then(function (version) {
                self.version = version;
            });
        },

    },{
        model:  'res.company',
        fields: [ 'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id' , 'country_id', 'state_id', 'tax_calculation_rounding_method'],
        ids:    function(self){ return [self.session.user_context.allowed_company_ids[0]]; },
        loaded: function(self,companies){ self.company = companies[0]; },
    },{
        model:  'decimal.precision',
        fields: ['name','digits'],
        loaded: function(self,dps){
            self.dp  = {};
            for (var i = 0; i < dps.length; i++) {
                self.dp[dps[i].name] = dps[i].digits;
            }
        },
    },{
        model:  'uom.uom',
        fields: [],
        domain: null,
        context: function(self){ return { active_test: false }; },
        loaded: function(self,units){
            self.units = units;
            _.each(units, function(unit){
                self.units_by_id[unit.id] = unit;
            });
        }
    },{
        model:  'res.partner',
        label: 'load_partners',
        fields: ['name','street','city','state_id','country_id','vat','lang',
                 'phone','zip','mobile','email','barcode','write_date',
                 'property_account_position_id','property_product_pricelist', 'customer_created_by', 'ref'],
        loaded: function(self,partners){
            self.partners = partners;
            self.db.add_partners(partners);
        },
    },{
        model:  'res.country.state',
        fields: ['name', 'country_id'],
        loaded: function(self,states){
            self.states = states;
        },
    },{
        model:  'res.country',
        fields: ['name', 'vat_label', 'code'],
        loaded: function(self,countries){
            self.countries = countries;
            self.company.country = null;
            for (var i = 0; i < countries.length; i++) {
                if (countries[i].id === self.company.country_id[0]){
                    self.company.country = countries[i];
                }
            }
        },
    },{
        model:  'res.lang',
        fields: ['name', 'code'],
        loaded: function (self, langs){
            self.langs = langs;
        },
    },{
        model:  'account.tax',
        fields: ['name','amount', 'price_include', 'include_base_amount', 'amount_type', 'children_tax_ids'],
        domain: function(self) {return [['company_id', '=', self.company && self.company.id || false]]},
        loaded: function(self, taxes){
            self.taxes = taxes;
            self.taxes_by_id = {};
            _.each(taxes, function(tax){
                self.taxes_by_id[tax.id] = tax;
            });
            _.each(self.taxes_by_id, function(tax) {
                tax.children_tax_ids = _.map(tax.children_tax_ids, function (child_tax_id) {
                    return self.taxes_by_id[child_tax_id];
                });
            });
            return new Promise(function (resolve, reject) {
              var tax_ids = _.pluck(self.taxes, 'id');
              self.rpc({
                  model: 'account.tax',
                  method: 'get_real_tax_amount',
                  args: [tax_ids],
              }).then(function (taxes) {
                  _.each(taxes, function (tax) {
                      self.taxes_by_id[tax.id].amount = tax.amount;
                  });
                  resolve();
              });
            });
        },
    },{
        model:  'pos.session',
        fields: ['id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at', 'sequence_number', 'payment_method_ids', 'cash_register_id', 'state'],
        domain: function(self){
            var domain = [
                ['state','in',['opening_control','opened']],
                ['rescue', '=', false],
            ];
            if (self.config_id) domain.push(['config_id', '=', self.config_id]);
            return domain;
        },
        loaded: function(self, pos_sessions, tmp){
            self.pos_session = pos_sessions[0];
            self.pos_session.login_number = odoo.login_number;
            self.config_id = self.config_id || self.pos_session && self.pos_session.config_id[0];
            tmp.payment_method_ids = pos_sessions[0].payment_method_ids;
        },
    },{
        model: 'pos.config',
        fields: [],
        domain: function(self){ return [['id','=', self.config_id]]; },
        loaded: function(self,configs){
            self.config = configs[0];
            self.config.use_proxy = self.config.is_posbox && (
                                    self.config.iface_electronic_scale ||
                                    self.config.iface_print_via_proxy  ||
                                    self.config.iface_scan_via_proxy   ||
                                    self.config.iface_customer_facing_display);

            self.db.set_uuid(self.config.uuid);
            self.set_cashier(self.get_cashier());
            // We need to do it here, since only then the local storage has the correct uuid
            self.db.save('pos_session_id', self.pos_session.id);

            var orders = self.db.get_orders();
            for (var i = 0; i < orders.length; i++) {
                self.pos_session.sequence_number = Math.max(self.pos_session.sequence_number, orders[i].data.sequence_number+1);
            }
       },
    },{
      model: 'stock.picking.type',
      fields: ['use_create_lots', 'use_existing_lots'],
      domain: function(self){ return [['id', '=', self.config.picking_type_id[0]]]; },
      loaded: function(self, picking_type) {
          self.picking_type = picking_type[0];
      },
    },{
        model:  'res.users',
        fields: ['name','company_id', 'id', 'groups_id', 'lang'],
        domain: function(self){ return [['company_ids', 'in', self.config.company_id[0]],'|', ['groups_id','=', self.config.group_pos_manager_id[0]],['groups_id','=', self.config.group_pos_user_id[0]]]; },
        loaded: function(self,users){
            users.forEach(function(user) {
                user.role = 'cashier';
                user.groups_id.some(function(group_id) {
                    if (group_id === self.config.group_pos_manager_id[0]) {
                        user.role = 'manager';
                        return true;
                    }
                });
                if (user.id === self.session.uid) {
                    self.user = user;
                    self.employee.name = user.name;
                    self.employee.role = user.role;
                    self.employee.user_id = [user.id, user.name];
                }
            });
            self.users = users;
            self.employees = [self.employee];
            self.set_cashier(self.employee);
        },
    },{
        model:  'product.pricelist',
        fields: ['name', 'display_name', 'discount_policy'],
        domain: function(self) {
            if (self.config.use_pricelist) {
                return [['id', 'in', self.config.available_pricelist_ids]];
            } else {
                return [['id', '=', self.config.pricelist_id[0]]];
            }
        },
        loaded: function(self, pricelists){
            _.map(pricelists, function (pricelist) { pricelist.items = []; });
            self.default_pricelist = _.findWhere(pricelists, {id: self.config.pricelist_id[0]});
            self.pricelists = pricelists;
        },
    },{
        model:  'account.bank.statement',
        fields: ['id', 'balance_start'],
        domain: function(self){ return [['id', '=', self.pos_session.cash_register_id[0]]]; },
        loaded: function(self, statement){
            self.bank_statement = statement[0];
        },
    },{
        model:  'product.pricelist.item',
        domain: function(self) { return [['pricelist_id', 'in', _.pluck(self.pricelists, 'id')]]; },
        loaded: function(self, pricelist_items){
            var pricelist_by_id = {};
            _.each(self.pricelists, function (pricelist) {
                pricelist_by_id[pricelist.id] = pricelist;
            });

            _.each(pricelist_items, function (item) {
                var pricelist = pricelist_by_id[item.pricelist_id[0]];
                pricelist.items.push(item);
                item.base_pricelist = pricelist_by_id[item.base_pricelist_id[0]];
            });
        },
    },{
        model:  'product.category',
        fields: ['name', 'parent_id'],
        loaded: function(self, product_categories){
            var category_by_id = {};
            _.each(product_categories, function (category) {
                category_by_id[category.id] = category;
            });
            _.each(product_categories, function (category) {
                category.parent = category_by_id[category.parent_id[0]];
            });

            self.product_categories = product_categories;
        },
    },{
        model: 'res.currency',
        fields: ['name','symbol','position','rounding','rate'],
        ids:    function(self){ return [self.config.currency_id[0], self.company.currency_id[0]]; },
        loaded: function(self, currencies){
            self.currency = currencies[0];
            if (self.currency.rounding > 0 && self.currency.rounding < 1) {
                self.currency.decimals = Math.ceil(Math.log(1.0 / self.currency.rounding) / Math.log(10));
            } else {
                self.currency.decimals = 0;
            }

            self.company_currency = currencies[1];
        },
    },{
        model:  'pos.category',
        fields: ['id', 'name', 'parent_id', 'child_id', 'write_date'],
        domain: function(self) {
            return self.config.limit_categories && self.config.iface_available_categ_ids.length ? [['id', 'in', self.config.iface_available_categ_ids]] : [];
        },
        loaded: function(self, categories){
            self.db.add_categories(categories);
        },
    },{
        model:  'product.product',
        fields: ['display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                 'barcode', 'default_code', 'to_weight', 'uom_id', 'sub_type_uom', 'quantity_uom', 'barcodes_related_ids', 'scan_in_pos', 'qty_available', 'description_sale', 'description',
                 'product_tmpl_id','tracking', 'write_date', 'available_in_pos', 'attribute_line_ids'],
        order:  _.map(['sequence','default_code','name'], function (name) { return {name: name}; }),
        domain: function(self){
            var domain = ['&', '&', ['sale_ok','=',true],['available_in_pos','=',true],'|',['company_id','=',self.config.company_id[0]],['company_id','=',false]];
            if (self.config.limit_categories &&  self.config.iface_available_categ_ids.length) {
                domain.unshift('&');
                domain.push(['pos_categ_id', 'in', self.config.iface_available_categ_ids]);
            }
            if (self.config.iface_tipproduct){
              domain.unshift(['id', '=', self.config.tip_product_id[0]]);
              domain.unshift('|');
            }
            return domain;
        },
        context: function(self){ return { display_default_code: false }; },
        loaded: function(self, products){
            var using_company_currency = self.config.currency_id[0] === self.company.currency_id[0];
            var conversion_rate = self.currency.rate / self.company_currency.rate;
            self.db.add_products(_.map(products, function (product) {
                console.log("stockkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk inv:", product.qty_available, " product:", product.display_name)
                if (!using_company_currency) {
                    product.lst_price = round_pr(product.lst_price * conversion_rate, self.currency.rounding);
                }
                product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                product.pos = self;
                return new models.Product({}, product);
            }));
        },
    },{
        model: 'product.attribute',
        fields: ['name', 'display_type'],
        condition: function (self) { return self.config.product_configurator; },
        domain: function(){ return [['create_variant', '=', 'no_variant']]; },
        loaded: function(self, product_attributes, tmp) {
            tmp.product_attributes_by_id = {};
            _.map(product_attributes, function (product_attribute) {
                tmp.product_attributes_by_id[product_attribute.id] = product_attribute;
            });
        }
    },{
        model: 'product.attribute.value',
        fields: ['name', 'attribute_id', 'is_custom', 'html_color'],
        condition: function (self) { return self.config.product_configurator; },
        domain: function(self, tmp){ return [['attribute_id', 'in', _.keys(tmp.product_attributes_by_id).map(parseFloat)]]; },
        loaded: function(self, pavs, tmp) {
            tmp.pav_by_id = {};
            _.map(pavs, function (pav) {
                tmp.pav_by_id[pav.id] = pav;
            });
        }
    }, {
        model: 'product.template.attribute.value',
        fields: ['product_attribute_value_id', 'attribute_id', 'attribute_line_id', 'price_extra'],
        condition: function (self) { return self.config.product_configurator; },
        domain: function(self, tmp){ return [['attribute_id', 'in', _.keys(tmp.product_attributes_by_id).map(parseFloat)]]; },
        loaded: function(self, ptavs, tmp) {
            self.attributes_by_ptal_id = {};
            _.map(ptavs, function (ptav) {
                if (!self.attributes_by_ptal_id[ptav.attribute_line_id[0]]){
                    self.attributes_by_ptal_id[ptav.attribute_line_id[0]] = {
                        id: ptav.attribute_line_id[0],
                        name: tmp.product_attributes_by_id[ptav.attribute_id[0]].name,
                        display_type: tmp.product_attributes_by_id[ptav.attribute_id[0]].display_type,
                        values: [],
                    };
                }
                self.attributes_by_ptal_id[ptav.attribute_line_id[0]].values.push({
                    id: ptav.product_attribute_value_id[0],
                    name: tmp.pav_by_id[ptav.product_attribute_value_id[0]].name,
                    is_custom: tmp.pav_by_id[ptav.product_attribute_value_id[0]].is_custom,
                    html_color: tmp.pav_by_id[ptav.product_attribute_value_id[0]].html_color,
                    price_extra: ptav.price_extra,
                });
            });
        }
    },{
        model: 'account.cash.rounding',
        fields: ['name', 'rounding', 'rounding_method'],
        domain: function(self){return [['id', '=', self.config.rounding_method[0]]]; },
        loaded: function(self, cash_rounding) {
            self.cash_rounding = cash_rounding;
        }
    },{
        model:  'pos.payment.method',
        fields: ['name', 'is_cash_count', 'use_payment_terminal'],
        domain: function(self, tmp) {
            return [['id', 'in', tmp.payment_method_ids]];
        },
        loaded: function(self, payment_methods) {
            self.payment_methods = payment_methods.sort(function(a,b){
                // prefer cash payment_method to be first in the list
                if (a.is_cash_count && !b.is_cash_count) {
                    return -1;
                } else if (!a.is_cash_count && b.is_cash_count) {
                    return 1;
                } else {
                    return a.id - b.id;
                }
            });
            self.payment_methods_by_id = {};
            _.each(self.payment_methods, function(payment_method) {
                self.payment_methods_by_id[payment_method.id] = payment_method;

                var PaymentInterface = self.electronic_payment_interfaces[payment_method.use_payment_terminal];
                if (PaymentInterface) {
                    payment_method.payment_terminal = new PaymentInterface(self, payment_method);
                }
            });
        }
    },{
        model:  'account.fiscal.position',
        fields: [],
        domain: function(self){ return [['id','in',self.config.fiscal_position_ids]]; },
        loaded: function(self, fiscal_positions){
            self.fiscal_positions = fiscal_positions;
        }
    }, {
        model:  'account.fiscal.position.tax',
        fields: [],
        domain: function(self){
            var fiscal_position_tax_ids = [];

            self.fiscal_positions.forEach(function (fiscal_position) {
                fiscal_position.tax_ids.forEach(function (tax_id) {
                    fiscal_position_tax_ids.push(tax_id);
                });
            });

            return [['id','in',fiscal_position_tax_ids]];
        },
        loaded: function(self, fiscal_position_taxes){
            self.fiscal_position_taxes = fiscal_position_taxes;
            self.fiscal_positions.forEach(function (fiscal_position) {
                fiscal_position.fiscal_position_taxes_by_id = {};
                fiscal_position.tax_ids.forEach(function (tax_id) {
                    var fiscal_position_tax = _.find(fiscal_position_taxes, function (fiscal_position_tax) {
                        return fiscal_position_tax.id === tax_id;
                    });

                    fiscal_position.fiscal_position_taxes_by_id[fiscal_position_tax.id] = fiscal_position_tax;
                });
            });
        }
    },  {
        label: 'fonts',
        loaded: function(){
            return new Promise(function (resolve, reject) {
                // Waiting for fonts to be loaded to prevent receipt printing
                // from printing empty receipt while loading Inconsolata
                // ( The font used for the receipt )
                waitForWebfonts(['Lato','Inconsolata'], function () {
                    resolve();
                });
                // The JS used to detect font loading is not 100% robust, so
                // do not wait more than 5sec
                setTimeout(resolve, 5000);
            });
        },
    },{
        label: 'pictures',
        loaded: function (self) {
            self.company_logo = new Image();
            return new Promise(function (resolve, reject) {
                self.company_logo.onload = function () {
                    var img = self.company_logo;
                    var ratio = 1;
                    var targetwidth = 300;
                    var maxheight = 150;
                    if( img.width !== targetwidth ){
                        ratio = targetwidth / img.width;
                    }
                    if( img.height * ratio > maxheight ){
                        ratio = maxheight / img.height;
                    }
                    var width  = Math.floor(img.width * ratio);
                    var height = Math.floor(img.height * ratio);
                    var c = document.createElement('canvas');
                    c.width  = width;
                    c.height = height;
                    var ctx = c.getContext('2d');
                    ctx.drawImage(self.company_logo,0,0, width, height);

                    self.company_logo_base64 = c.toDataURL();
                    resolve();
                };
                self.company_logo.onerror = function () {
                    reject();
                };
                self.company_logo.crossOrigin = "anonymous";
                self.company_logo.src = '/web/binary/company_logo' + '?dbname=' + self.session.db + '&company=' + self.company.id + '&_' + Math.random();
            });
        },
    }, {
        label: 'barcodes',
        loaded: function(self) {
            var barcode_parser = new BarcodeParser({'nomenclature_id': self.config.barcode_nomenclature_id});
            self.barcode_reader.set_barcode_parser(barcode_parser);
            return barcode_parser.is_loaded();
        },
    },
    ],

    load_series: function (configId=0) {
        var self = this
        this.rpc({
            model: 'pos.order',
            method: 'get_series_pos_order',
            args: [configId],
        }).then(function (result) {
            console.log("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii 1 ", result, "   config_id:",configId)
            if(result.length > 0){
                console.log("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii 2 ", result)
                self.db.save_series(result)    
            }
        });
    },
    get_repart: function() {
        var order = this.get_order();
        if (order) {
            return order.get_repart();
        }
        return null;
    },
});

models.Product = models.Product.extend({
    // Nueva función js
    get_count_product_x_caja: function() {
        return this.quantity_uom;
    },
    // Nueva función js
    get_count_unidades_inv: function() {
        return this.qty_available;
    },
    // Nueva función js
    get_unit_caja: function() {
        var sub_unidad_medida = this.sub_type_uom;
        if(!sub_unidad_medida){
            return '';
        }
        sub_unidad_medida = sub_unidad_medida[0];
        if(!this.pos){
            return undefined;
        }
        return this.pos.units_by_id[sub_unidad_medida];       
    },
});

var _super_orderline = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    initialize: function(attr,options){
        this.qty_caja = 0;
        this.qtyCajaStr = '0';
        this.qty_inv = 0;
        this.qtyInvStr = '0';
        _super_orderline.initialize.apply(this,arguments);
    },
    init_from_JSON: function(json) {
        this.set_qty_caja(json.qty_caja);
        this.set_qty_inv(json.qty_inv);
        _super_orderline.init_from_JSON.apply(this,arguments);
    },
    export_as_JSON: function() {
        // var json = _super_orderline.export_as_JSON.apply(this,arguments);
        var json = _super_orderline.export_as_JSON.bind(this)();
        var to_return = _.extend(json, {
            qty_product_x_caja: this.get_count_product_x_caja(),
            qty_caja: this.get_qty_caja(),
            qty_inv: this.get_qty_inv(),
        });
        return to_return;
    },
    clone: function(){
        var json = _super_orderline.clone.apply(this,arguments);
        json.qty_caja = this.qty_caja;
        json.qty_inv = this.qty_inv;
        return json
    },
    // Nueva función js
    // sets a qty caja
    set_qty_caja: function(qty_caja){
        this.order.assert_editable();
        if(qty_caja === 'remove'){
            this.order.remove_orderline(this);
            return;
        }
        var quant_caja = typeof(qty_caja) === 'number' ? qty_caja : (field_utils.parse.float('' + qty_caja) || 0);
        this.qty_caja = quant_caja;
        this.qtyCajaStr = '' + quant_caja;
        this.trigger('change',this);
    },
    // Nueva función js
    // returns the qty caja
    get_qty_caja: function(){
        return this.qty_caja;
    },
    // Nueva función js
    get_qty_caja_str: function(){
        return this.qtyCajaStr;
    },
    // Nueva función js
    // sets a qty inv
    set_qty_inv: function(quant_inv){
        this.order.assert_editable();
        this.qty_inv = quant_inv;
        this.qtyInvStr = '' + quant_inv;
        this.trigger('change',this);
    },
    // Nueva función js
    // returns the qty inv
    get_qty_inv: function(){
        return this.qty_inv;
    },
    get_qty_inv_: function(){
        var quantity = this.get_quantity()
        var total_quantity_x_cajas = this.get_total_quantity_x_cajas()
        var total_products = quantity + total_quantity_x_cajas
        if(!this.get_unit_caja() || this.get_count_product_x_caja() <= 1 || total_products > this.get_count_unidades_inv()){
            this.set_qty_caja(0)
            this.set_qty_inv(quantity)
        }
        this.set_qty_inv(total_products)
        return this.get_count_unidades_inv() - this.get_qty_inv();
    },
    // Nueva función js
    get_qty_inv_str: function(){
        return this.qtyInvStr;
    },
    // Nueva función js
    get_total_quantity_x_cajas: function(){
        return parseInt(this.get_qty_caja() * this.get_count_product_x_caja());
    },
    // Función del POS
    // when we add an new orderline we want to merge it with the last line to see reduce the number of items
    // in the orderline. This returns true if it makes sense to merge the two
    can_be_merged_with: function(orderline){
        var price = parseFloat(round_di(this.price || 0, this.pos.dp['Product Price']).toFixed(this.pos.dp['Product Price']));
        var order_line_price = orderline.get_product().get_price(orderline.order.pricelist, (this.get_total_quantity_x_cajas() + this.get_quantity()));
        order_line_price = orderline.compute_fixed_price(order_line_price);
        if( this.get_product().id !== orderline.get_product().id){    //only orderline of the same product can be merged
            return false;
        }else if(!this.get_unit() || !this.get_unit().is_pos_groupable){
            return false;
        }else if(this.get_discount() > 0){             // we don't merge discounted orderlines
            return false;
        }else if(!utils.float_is_zero(price - order_line_price - orderline.get_price_extra(),
                    this.pos.currency.decimals)){
            return false;
        }else if(this.product.tracking == 'lot' && (this.pos.picking_type.use_create_lots || this.pos.picking_type.use_existing_lots)) {
            return false;
        }else if (this.description !== orderline.description) {
            return false;
        }else{
            return true;
        }
    },
    // Función del POS
    get_base_price:    function(){
        var rounding = this.pos.currency.rounding;
        return round_pr(this.get_unit_price() * (this.get_total_quantity_x_cajas() + this.get_quantity()) * (1 - this.get_discount()/100), rounding);
    },
    // Función del POS
    get_all_prices: function(){

        var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
        var taxtotal = 0;

        var product =  this.get_product();
        var taxes_ids = _.filter(product.taxes_id, t => t in this.pos.taxes_by_id);
        var taxdetail = {};
        var product_taxes = this.get_taxes_after_fp(taxes_ids);

        var all_taxes = this.compute_all(product_taxes, price_unit, (this.get_total_quantity_x_cajas() + this.get_quantity()), this.pos.currency.rounding);
        var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), (this.get_total_quantity_x_cajas() + this.get_quantity()), this.pos.currency.rounding);
        _(all_taxes.taxes).each(function(tax) {
            taxtotal += tax.amount;
            taxdetail[tax.id] = tax.amount;
        });

        return {
            "priceWithTax": all_taxes.total_included,
            "priceWithoutTax": all_taxes.total_excluded,
            "priceSumTaxVoid": all_taxes.total_void,
            "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
            "tax": taxtotal,
            "taxDetails": taxdetail,
        };
    },
    // Nueva función js
    get_unit_caja: function(){
        return this.product.get_unit_caja();
    },
    // Nueva función js
    get_count_product_x_caja: function(){
        return this.product.get_count_product_x_caja();
    },
    // Nueva función js
    get_count_unidades_inv: function(){
        return this.product.get_count_unidades_inv();
    },
});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function(attributes,options){
        this.set({ tipo_compra: null});
        this.set({ repart: null});
        console.log("|||||||||||||||||||||||||||||||||||||||||||||||||||||| ", options.json)
        if (options.json === undefined) {
            console.log("initialize cuando se agegar nuevo pedidoo ", options.pos.config_id)
            var config_id = options.pos.config_id
            options.pos.load_series(config_id)
        } else {
            console.log("initialize cuando recarga paginaa ", options.json)
        }
        _super_order.initialize.apply(this,arguments);
    },
    init_from_JSON: function(json) {
        var serie_id;
        console.log("init_from_JSON 1, ", json.serie_id)
        if (json.serie_id !== false) {
            console.log("init_from_JSON 2, ", json.serie_id)
            var lista_series = this.pos.db.get_series()
            console.log("qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq ", lista_series)
            for(var i=0, len=lista_series.length; i<len; i++){
                if(lista_series[i].id == json.serie_id){
                    serie_id = lista_series[i]
                }
            }
            console.log("}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}} ", serie_id)
            if (!serie_id) {
                console.error('ERROR: intentando cargar una serie no disponible en la pos');
            }
        } else {
            console.log("init_from_JSON 3, ", json.serie_id)
            serie_id = null;
        }
        console.log("init_from_JSON 4 ", serie_id)
        this.set_tipo_compra(serie_id);
        var repart;
        if (json.repart !== false) {
            repart = this.pos.db.get_partner_by_id(json.repart);
            if (!repart) {
                console.error('ERROR: intentando cargar un repartidor no disponible en la pos');
            }
        } else {
            repart = null;
        }
        this.set_repart(repart);
        _super_order.init_from_JSON.apply(this,arguments);
    },
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.bind(this)();
        var to_return = _.extend(json, {
            repart: this.get_repart() ? this.get_repart().id : false,
            serie_id: this.get_tipo_compra() ? this.get_tipo_compra().id : false,
        });
        console.log("export_as_JSON ", to_return)
        return to_return;
    },
    set_tipo_compra: function(tipo_compra){
        console.log("set_tipo_compra ", tipo_compra)
        this.assert_editable();
        this.set('tipo_compra',tipo_compra);
    },
    get_tipo_compra: function(){
        console.log("get_tipo_compra ", this.get('tipo_compra'))
        return this.get('tipo_compra');
    },
    get_tipo_compra_name: function(){
        console.log("get_tipo_compra_name ", this.get('tipo_compra'))
        var tipo_compra = this.get('tipo_compra');
        return tipo_compra ? tipo_compra.data : "";
    },
    set_repart: function(repart){
        this.assert_editable();
        this.set('repart',repart);
    },
    get_repart: function(){
        return this.get('repart');
    },
    get_repart_name: function(){
        var repart = this.get('repart');
        return repart ? repart.name : "";
    },
    get_serie_bd: function(indice_nuevo){
        var lista_series = this.pos.db.get_series()
        if(lista_series.length == 0){
            const names = [{ id: 1, text: 'Joseph'}, { id: 2, text: 'Kaykay' }];
            Gui.showPopup('ModalDialog', {
                body: _t(
                    'No es posible seleccionar un tipo de compra, ya que no tiene series relacionadas a las compras al Mayoreo y Minoreo.'
                ),
            });
        } else {
            console.log("ttttttttttttttttttttttttttttttttttttttttttttttt ", lista_series)
            for(var i=0, len=lista_series.length; i<len; i++){
                console.log("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< ", lista_series[i].indice, " == ", indice_nuevo)
                if(lista_series[i].indice == indice_nuevo){
                    console.log("entrooooooooooooooooooooooooooooo ", lista_series[i])
                    return  lista_series[i]
                }
            }
        }
    },
    load_series: function() {
        var config_id = this.pos.config_id
        console.log("1111111111111111111111111111111111111111111111111234543456789876543 ", config_id)
        this.pos.load_series(config_id)
    },
    export_for_printing: function () {
        var receipt = _super_order.export_for_printing.bind(this)();
        var repart_  = this.get('repart');
        console.log("export_for_printing")
        receipt = _.extend(receipt, {
            repart: repart_ ? repart_.name : null,
        });
        return receipt;
    },
    add_product: function(product, options){
        _super_order.add_product.apply(this, arguments);
        console.log("000000000000000000000000000000000000000000000000 ", product)
        if(options.qty_caja !== undefined){
            console.log("ingresar caja a 11111111111111111111111111:::::::::::::..")
            this.pos.get_order().get_selected_orderline().set_qty_caja(options.qty_caja);
        }
    },
});

});