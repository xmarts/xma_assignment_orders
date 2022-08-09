# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Objeto para guardar impuestos desglozados en pedidos de venta.
class SaleLineTax (models.Model):

    _name='sale.line.tax'
    _description = 'Data of taxes related to purchase'

    name = fields.Char(string="Nombre impuesto", readonly=True) 
    monto_base = fields.Char(string="Monto base", readonly=True)
    total_impuesto = fields.Char(string="Total Impuesto", readonly=True) 
    sale_related=fields.Many2one('sale.order', string="Venta relacionada",  index=True, ondelete='cascade')