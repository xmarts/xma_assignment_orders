# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
#Añadido para complementar integración SIA-ODOO en secuencias.
class IrSequence(models.Model):

	_inherit='ir.sequence'

	relation_id = fields.Many2one('ir.model',string="Uso", store=True)
	description = fields.Char(String="Descripción")
	serie = fields.Char(String="Serie")
	ptv_related_id = fields.Many2one('pos.config', string="Punto de venta relacionado", store=True)

	@api.onchange('description','serie')
	def onchange_name_auto(self):
		print ("Ingresa al onchange en sequence",self)
		for sequence in self:
			sequence.name = str(sequence.serie) + " - " + str(sequence.description)

	

