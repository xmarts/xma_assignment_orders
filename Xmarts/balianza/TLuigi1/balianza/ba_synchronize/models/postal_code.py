# -*- coding: utf-8 -*-
from odoo import fields, models

class PostalCode(models.Model):
	_name = 'postal.code'
	_description = 'Postal code and colonies'
	_order = 'name'

	name = fields.Char("Nombre colonia", required=True)
	zipcode = fields.Char("Codigo postal", required=True)
	country_id = fields.Many2one('res.country', string='Pais', required=True)
	state_id = fields.Many2one('res.country.state', string="Estado", domain="[('country_id', '=', country_id)]", required=True)
	city_id = fields.Many2one('res.city', string="Municipio", domain="[('state_id', '=', state_id)]",required=True)
	code_colony = fields.Char(string="Codigo colonia")