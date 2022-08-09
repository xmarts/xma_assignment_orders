# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
#Concatenación de codigo con nombre de lista de precios.
class ProductPricelist(models.Model):

	_inherit='product.pricelist'

	code = fields.Char(string="Codigo")

	def name_get(self):
		return [(pricelist.id, '%s / %s (%s)' % (pricelist.code,pricelist.name, pricelist.currency_id.name)) for pricelist in self]

#Funcionalidad agregada para modificación cambio de precios en base a precio por empaque y descuento, restricciones al modificar precios de productos.
class ProductPricelistItem(models.Model):

	_inherit='product.pricelist.item'

	price_unidad = fields.Float(string="Precio empaque")
	percent_discount_unidad = fields.Float(string="Porcentaje de descuento")
	price_sub_unidad = fields.Float(related='fixed_price', string="Precio por unidad con descuento")
	limit_update_price = fields.Boolean(string="Limite personalizado actualización de precio", store=True)
	type_limit = fields.Selection([('amount', 'Monto'), ('percent', 'Porcentaje')], string="Tipo limite actualización de precios")
	amount_update_limit_up = fields.Integer(string="Cantidad máxima aumento de precio",store=True,copy=False)
	percent_update_limit_up =  fields.Integer(string="Porcentaje máximo aumento de precio",store=True,copy=False)
	amount_update_limit_down = fields.Integer(string="Cantidad máxima diminución de precio",store=True,copy=False)
	percent_update_limit_down =  fields.Integer(string="Porcentaje máximo diminución de precio",store=True,copy=False)

	@api.onchange('price_unidad','percent_discount_unidad')
	def onchange_price_percent_unidad(self):
		if self.percent_discount_unidad < 0:
			raise ValidationError("No se puede agregar un descuento negativo.")
		if self.percent_discount_unidad > 100:
			raise ValidationError("No se puede agregar un descuento mayor al 100%")
		if self.price_unidad < 0:
			raise ValidationError("No se puede agregar un precio negativo.")
		if self.price_unidad:
			self.fixed_price = (self.price_unidad * ((100-self.percent_discount_unidad)/100)) / self.product_tmpl_id.quantity_uom

	@api.model_create_multi
	def create(self, vals_list):
		pricelist_item = super(ProductPricelistItem, self).create(vals_list)
		vals = vals_list[0]
		#print ("Esto es vals_list",vals_list)
		#print ("Esto es product_tmpl_id",vals['product_tmpl_id'])
		#print ("Esto es pricelist_id",vals['pricelist_id'])
		previously_created = self.env['product.pricelist.item'].search([('product_tmpl_id','=',vals['product_tmpl_id']),('pricelist_id','=',vals['pricelist_id'])])
		if len(previously_created) >= 2:
			raise ValidationError("El producto:" + str(self.env['product.template'].search([('id','=',vals['product_tmpl_id'])]).name) + " Ya se encuentra agregado en los registros de lista de precios." )
		return pricelist_item
