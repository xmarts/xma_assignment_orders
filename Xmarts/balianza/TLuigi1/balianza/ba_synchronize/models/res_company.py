# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


#Añadido para complementar integración SIA-ODOO en compañias.
class ResCompany (models.Model):

    _inherit='res.company'

    company_code = fields.Char(string="Codigo compañia",store = True) 