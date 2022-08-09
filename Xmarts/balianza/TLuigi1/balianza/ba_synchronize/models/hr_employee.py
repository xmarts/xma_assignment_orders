# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

#Añadido para complementar integración SIA-ODOO en empleados.
class HrEmployee(models.Model):

	_inherit='hr.employee'

	code = fields.Char(string="Codigo empleado")