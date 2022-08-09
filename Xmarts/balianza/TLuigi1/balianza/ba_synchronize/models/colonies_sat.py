# -*- coding: utf-8 -*-
from odoo import fields, models

class ColoniesSat(models.Model):
	_name = 'colonies.sat'
	_description = 'Colonies SAT'
	_order = 'name'

	name = fields.Char("Nombre colonia", required=True)
	zipcode = fields.Char("Codigo postal", required=True)
	code_colony = fields.Char(string="Codigo colonia")