# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _, modules
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError

#Codigo mostrar disponibilidad de pedidos delivery porcentaje de productos en punto de venta y desgloce de productos disponibles.
class SaleDeliveryAvailableBa(models.Model):

	_name='sale.delivery.available.ba'
	
	delivery_stock_line_ids = fields.One2many('sale.delivery.available.line.ba','delivery_stock_id',string="Productos relacionados")
	pos_id = fields.Many2one('pos.config',string="Punto de venta")
	percentage_order = fields.Float(string='Porcentaje pedido', store=True)
	distance = fields.Float(string='Distancia (KM)', store=True)
	price_delivery = fields.Float(string='Costo envio', store=True)
	delivery_id = fields.Many2one('sale.delivery.ba',string="Delivery related")

	def action_create_pos_order(self):
		print ("Esto es action_create_pos_order")
	
class SaleDeliveryAvailableLineBa(models.Model):

	_name='sale.delivery.available.line.ba'

	product_id = fields.Many2one('product.product',string="Producto")
	quantity_unit = fields.Char(string="Unidades por empaque", compute="_compute_quantity_unit", store=True)
	unidad_requested  = fields.Integer(string="Cajas solicitadas", default = 0)
	sub_unidad_requested = fields.Integer(string="Unidades solicitadas", default = 0)
	unidad = fields.Integer(string="Cajas disponibles", default = 0)
	sub_unidad = fields.Integer(string="Unidades disponibles", default = 0)
	delivery_stock_id = fields.Many2one('sale.delivery.available.ba',string="Delivery stock related")