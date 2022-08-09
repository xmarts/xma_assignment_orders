# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

#Modificaciones para tener control de almacenes y ubicaciones, solamente un almacen permitido por empresa y multiples ubicaciones como almacenes.
class stockLocation(models.Model):

	_inherit='stock.location'

	code = fields.Char(string="Codigo almacen", required=True, size=10, help="Codigo de almacen en SIA")
	code_ptv = fields.Char(string="Codigo punto de venta")
	location_position_id = fields.One2many('stock.location.position', 'location_related', string="Ubicaciones", store=True)
	sequence = fields.Integer(string="Secuencia")

class StockLocationPosition(models.Model):
	
	_name = "stock.location.position"

	name = fields.Many2one('stock.position', string="Ubicación",index=True, ondelete='cascade')
	sub_positions_ids = fields.One2many(related='name.subpositions_related',string="Sub-Ubicaciones")
	location_related = fields.Many2one('stock.location',  index=True, ondelete='cascade')
	
class StockPosition(models.Model):
	
	_name ='stock.position'

	name = fields.Char(string="Nombre del lugar")
	location_position_id=fields.One2many('stock.location.position', 'name', string="Potition related", store=True)
	subpositions_related=fields.One2many('stock.subposition', 'position_id', string="Sub-ubicaciones relacionadas", store=True)

class StockSubPosition(models.Model):
	
	_name ='stock.subposition'

	name = fields.Char(string="Nombre la posición")
	position_id = fields.Many2one('stock.position', string="Ubicación",  index=True, ondelete='cascade')