# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

#Añadido para complementar integración SIA-ODOO en departamentos.
class HrDepartment(models.Model):

	_inherit='hr.department'

	code = fields.Char(string="Codigo departamento") 