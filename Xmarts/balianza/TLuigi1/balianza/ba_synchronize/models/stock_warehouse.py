# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

#Modificación donde solo se permite tener un almacen global por razón social y codigo más largo en almacenes.

class stockWarehouse(models.Model):

	_inherit='stock.warehouse'

	code = fields.Char('Short Name', required=True, size=10, help="Short name used to identify your warehouse")

	@api.model
	def create(self, vals):
		warehouse = super(stockWarehouse, self).create(vals)
		#print ("Esto es vals",vals['company_id'])
		#print ("esto son los almacenes existentes", self.env.user.company_id.id)
		if vals['company_id'] == self.env.user.company_id.id:
			raise UserError('Solo puede existir un registro de almacen razon social por empresa') 

		return warehouse