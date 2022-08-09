# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Codigo para adecuaciones de integración SIA-ODOO.
class ProductTemplate(models.Model):
    _inherit='product.template'

    from_sia = fields.Boolean(string="Creado desde SIA?", store=True, readonly=True)
    sub_type = fields.Many2one('ba.sub.type.product', string="Subtipo de producto")
    sub_type_uom = fields.Many2one('uom.uom', string="Sub-unidad de medida")
    quantity_uom = fields.Integer(string="Cantidad por unidad de medida",default=1)
    packaging_content = fields.Integer(string="Contenido por empaque", readonly=True, compute='_compute_quantities')
    packing_quantity = fields.Integer(string="Cantidad empaque", readonly=True, compute='_compute_quantities')
    packing_unit_id = fields.Many2one('uom.uom', string="Unidad empaque", readonly=True, compute='_compute_quantities')
    quantity_unit = fields.Integer(string="Cantidad unidad", readonly=True, compute='_compute_quantities')
    unit_id = fields.Many2one('uom.uom', string="Unidad", readonly=True, compute='_compute_quantities')
    cantidades_reservadas_total = fields.Integer(string="Cantidad reservada",store=True)
    cantidades_reservadas = fields.Integer(string="Cantidad reservada en pedidos sin confirmar",store=True,copy=False)
    reserved_related_ids = fields.One2many('reserved.product', 'product_id', store=True)
    grados_alcohol = fields.Float(string="Grados de alcohol (%)")
    contenido = fields.Integer(string="Contenido")
    height = fields.Integer(string="Altura")
    width = fields.Integer(string="Ancho")
    length = fields.Integer(string="Largo")
    unit_id =  fields.Many2one('uom.uom', string="Unidad")
    costing_method = fields.Selection([('total_included', 'Total'), ('total_excluded', 'Subtotal'), ('total_void', 'Solo IEPS')], required=True, default='total_excluded')
    barcodes_related_ids = fields.One2many('barcodes.product','product_id',string="Codigos de barras")
    displacement_level_id = fields.Many2one('displacement.level',string="Clasificación")

    def calculate_reserved_quantity_ba(self):
        print ("Ingresa a calculate_reserved_quantity_ba",self)
        sales = self.env['sale.order.line'].search([('state','in',('sale','draft','sent','done')),('product_id.product_tmpl_id','=',self.id)])
        reservado = 0
        #print ("Esto es sales",sales)
        for sale in sales:
            #print ("Esto es sale.product_uom_qty",sale.product_uom_qty)
            #print ("Esto es sale.qty_delivered",sale.qty_delivered)
            reservado = reservado + (sale.product_uom_qty - sale.qty_delivered)
        self.cantidades_reservadas_total = reservado

    @api.depends_context('company')
    def _compute_quantities(self):
        res = self._compute_quantities_dict()
        for template in self:
            template.calculate_reserved_quantity_ba()
            template.qty_available = res[template.id]['qty_available']
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.outgoing_qty = res[template.id]['outgoing_qty']
            template.unit_id = template.uom_id.id
            template.packing_unit_id =  template.sub_type_uom.id
            template.packaging_content = template.quantity_uom
            if template.quantity_uom == 0:
                template.packing_quantity  = 0
                template.quantity_unit = 0

            if template.qty_available > 0 and template.quantity_uom != 0:
                template.packing_quantity = int(template.qty_available / template.quantity_uom)
                if template.packing_quantity > 0:
                    template.quantity_unit = template.qty_available - (template.packing_quantity *  template.quantity_uom)
                else:
                    template.quantity_unit = template.qty_available
            if template.qty_available < 0 and template.quantity_uom != 0:
                template.packing_quantity = int(template.qty_available / template.quantity_uom)
                if template.packing_quantity < 0:
                    template.quantity_unit = template.qty_available - (template.packing_quantity *  template.quantity_uom)
                else:
                    template.quantity_unit = template.qty_available
            if template.qty_available == 0:
                template.packing_quantity = 0
                template.quantity_unit = 0

    
    @api.model_create_multi
    def create(self, vals_list):
        val = vals_list[0]
        if "quantity_uom" in str(val):
            if int(val['quantity_uom']) == 0:
                raise ValidationError(_('El valor agregado en el campo Cantidad por unidad de medida no puede ser igual a 0, si la cantidad de unidad es igual a la cantidad de empaque puede añadir el valor de 1'))
        templates = super(ProductTemplate, self).create(vals_list)
        if templates:
            #print ("Esto es templates",templates)
            listas_precios = self.env['product.pricelist'].search([])
            #print ("Esto es lists de precios",listas_precios)
            moneda_id = self.env['res.currency'].search([('name','=','MXN')])
            for lista in listas_precios:
                #print ("Esto es lista",lista)
                values = {
                'product_tmpl_id':templates.id,
                'product_id': False,
                'categ_id':False,
                'min_quantity':0,
                'applied_on':'1_product',
                'base':'list_price',
                'base_pricelist_id':False,
                'pricelist_id':lista.id,
                'price_surcharge':0,
                'price_discount':0,
                'price_round':0,
                'price_min_margin':0,
                'price_max_margin':0,
                'company_id':False,
                'currency_id':moneda_id.id,
                'active':True,
                'date_start':False,
                'date_end':False,
                'compute_price':'fixed',
                'fixed_price':0,
                'percent_price':0,
                'price_unidad':0,
                'percent_discount_unidad':0,
                }
                self.env['product.pricelist.item'].create(values)

        return templates

class ProductProduct(models.Model):
    _inherit='product.product'

    def name_get(self):
        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []
        self.sudo().read(['name', 'default_code', 'product_tmpl_id'], load=False)

        product_template_ids = self.sudo().mapped('product_tmpl_id').ids
        if partner_ids:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                ('product_tmpl_id', 'in', product_template_ids),
                ('name', 'in', partner_ids),
                ])
            supplier_info.sudo().read(['product_tmpl_id', 'product_id', 'product_name', 'product_code'], load=False)
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)
        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                        'id': product.id,
                        'name': seller_variant or name,
                        'default_code': s.product_code or product.default_code,
                        }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                    'id': product.id,
                    'name': name,
                    'default_code': product.default_code,
                    }
                result.append(_name_get(mydict))
        return result

class ProductCategory(models.Model):
    _inherit='product.category'

    category_code = fields.Char(string="Codigo categoria", store=True, readonly=True)

class ReservedProduct(models.Model):

    _name='reserved.product'
    _description = 'Productos reservados'

    order_id = fields.Many2one('sale.order', string="Pedido", required=True)
    product_id = fields.Many2one('product.template', string='Producto', required=True)
    cantidad = fields.Integer(string="Cantidad", required=True)

class SubTypeProduct(models.Model):

    _name='ba.sub.type.product'
    _description = 'Subtipo de producto'

    name = fields.Char(string='Descripción', required=True)
    code = fields.Char(string='Codigo', required=True)
