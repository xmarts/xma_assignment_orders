# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCitySat(models.Model):

	_name = 'res.city.sat'
	_description = 'Cities SAT'
	_order = 'name'

	name = fields.Char("Nombre ciudad", required=True)
	country_id = fields.Many2one('res.country', string='Pais', required=True)
	state_id = fields.Many2one('res.country.state', string="Estado", domain="[('country_id', '=', country_id)]", required=True)