# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
#Añadido para complementar integración SIA-ODOO en usuarios.
class ResUsers(models.Model):

	_inherit='res.users'

	user_code_id = fields.Char(string="Codigo Usuario") 
	point_sale_ids = fields.Many2many('pos.config', string='Puntos de venta permitidos',copy=False)