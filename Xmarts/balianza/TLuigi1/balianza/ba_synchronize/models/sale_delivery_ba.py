# -*- coding: utf-8 -*-
import requests
from odoo import api, fields, models, SUPERUSER_ID, _, modules



from datetime import datetime, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError


# Codigo control de pedidos delivery asignación de punto de venta con disponibilidad de producto.
class SaleDeliveryBa(models.Model):
    _name = 'sale.delivery.ba'

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Asignado'),
        ('cancel', 'Cancelado'),
    ], string='Estatus', readonly=True, copy=False, index=True, tracking=3, default='draft')
    user_id = fields.Many2one(
        'res.users', string='Vendedor', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id)])
    partner_id = fields.Many2one('res.partner', string="Cliente", store=True)

    serie_id = fields.Many2one('ir.sequence', string="Serie", store=True)
    delivery_line_ids = fields.One2many('sale.delivery.line.ba', 'delivery_id', string="Productos relacionados")
    company_id = fields.Many2one('res.company', string="Empresa")
    amount_untaxed = fields.Monetary(string='Monto base', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_by_group = fields.Binary(string="Impuestos", compute='_amount_by_group',
                                    help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Total impuestos', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True, readonly=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True)
    delivery_stock_ids = fields.One2many('sale.delivery.available.ba', 'delivery_id',
                                         string="Puntos de venta disponibles")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.pricelist_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False

    @api.depends('delivery_line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.delivery_line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def delivery_reasignation(self):
        #realizar query de ubicacion de delivery, el repartidor debe estar activo y el pdv cerca del repartidor
        query = 'select ST_Distance(ca.geolocation, hr_jax.geolocation) as distance from client_addresses ca, ' \
                'lateral(select id, geolocation from client_addresses where res_partner_id = (%s)) as hr_jax ' \
                'where ca.id <> hr_jax.id order by distance'



    def action_search_stock_in_points_of_sale(self):
        _inherit = 'res.config.settings'


        partner = self.partner_id.id  # Obtiene el id del cliente
        pdv_list = []
        pdv_radio = 4000 #obtener pdv_radio de pos_config

        query = 'select ST_Distance(ca.geolocation, hr_jax.geolocation) as distance from client_addresses ca, ' \
                'lateral(select id, geolocation from client_addresses where res_partner_id = (%s)) as hr_jax ' \
                'where ca.id <> hr_jax.id order by distance'

        #Ejecuta query para la selección de ruta lineal
        self._cr.execute(query, (partner, pdv_radio,))

        index = 0
        for res in self.env.cr.fetchall():
            pdv_list.append(res)
            index += 1

        #Se deben obtener estos valores
        is_pdv_available = 1
        is_pdv_on_service  = 1

        product_availability = [] #Este valor es la cantidad de productos disponibles en el PDV, se debe obtener de la API?
        product_availability.sort(reverse=True) #obtiene la lista de productos, de mayor a menor

        if float(pdv_list[0]) < pdv_radio and is_pdv_available == 1 and is_pdv_on_service == 1 and product_availability[0]:
        #Se debe agregar a productos disponibles
        if float(pdv_list[0]) > pdv_radio and is_pdv_available == 1:
        #agregar a productos disponibles, dejando que el cliente decida si lo quiere o no
        if is_pdv_available == 0:
            print('')

        print("Ingresa a buscar disponibilidad")
        points_of_sale = self.env['pos.config'].search([('id', 'in', (2204, 2203, 2264))])
        for point_of_sale in points_of_sale:
            print("Esto es el punto de venta", point_of_sale)
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api', '=', 'stock_in_points_of_sale')])
        if api:
            # print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
            }
            information = {
                "description": "Sincronización de huella logística",
                "type": "Sincronización inicial",
                "from_system": "SIA",
                "liga": self,
                "user_id": self.env.user.name,
                "company": self.env.user.company_id.company_code,
                "model": "product.template"
            }

            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: ' + api_url_company))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API stock_in_points_of_sale'))
        else:
            raise ValidationError("No se encontró el API stock_in_points_of_sale")


class SaleDeliveryLineBa(models.Model):
    _name = 'sale.delivery.line.ba'

    product_id = fields.Many2one('product.product', string="Producto")
    quantity_unit = fields.Char(string="Unidades por empaque", compute="_compute_quantity_unit", store=True)
    unidad = fields.Integer(string="Cajas", default=0)
    sub_unidad = fields.Integer(string="Unidades", default=0)
    pricelist_id = fields.Many2one('product.pricelist', string="L.P.")
    pricelist_name = fields.Char(related='pricelist_id.code', string="L.P.")
    box_price = fields.Float(string="Precio caja")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=0,
                                   copy=False)
    cantidad = fields.Float(string="Cantidad", related='product_uom_qty')
    delivery_id = fields.Many2one('sale.delivery.ba', string="Delivery related")
    grados_alcohol = fields.Float(string="Grados alcohol", default=0)
    contenido = fields.Integer(string="Contenido", default=0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    currency_id = fields.Many2one(related='delivery_id.currency_id', depends=['delivery_id.currency_id'], store=True,
                                  string='Currency', readonly=True)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.delivery_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.delivery_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.onchange('product_id')
    def product_id_change(self):

        if self.product_id:
            self.tax_id = self.product_id.taxes_id
            if not self.delivery_id.partner_id:
                raise ValidationError(_('No ha seleccionado el cliente.'))
            self.grados_alcohol = self.product_id.grados_alcohol
            self.contenido = self.product_id.contenido
            self.quantity_unit = str(self.product_id.quantity_uom) + " " + str(self.product_id.uom_id.name)
            self.pricelist_id = self.delivery_id.pricelist_id.id
            # pendiente
            tarifa = self.env['product.pricelist.item'].search(
                [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                 ('pricelist_id', '=', self.pricelist_id.id)])
            if tarifa:
                self.box_price = tarifa.price_unidad
            else:
                self.box_price = 0
        else:
            self.quantity_unit = ""

        self.product_uom_qty = 0
        self.unidad = 0
        self.sub_unidad = 0
