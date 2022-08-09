# -*- coding: utf-8 -*-
from odoo import fields, models

class PostalCodeSat(models.Model):
	_name = 'postal.code.sat'
	_description = 'Postal code sat and colonies'
	_order = 'name'

	name = fields.Char("Nombre colonia", required=True)
	zipcode = fields.Char("Codigo postal", required=True)
	country_id = fields.Many2one('res.country', string='Pais', required=True)
	state_id = fields.Many2one('res.country.state', string="Estado", domain="[('country_id', '=', country_id)]", required=True)
	city_id = fields.Many2one('res.city', string="Municipio", domain="[('state_id', '=', state_id)]",required=True)
	colony_sat_id = fields.Many2one('colonies.sat', string="Colony sat related",required=True)