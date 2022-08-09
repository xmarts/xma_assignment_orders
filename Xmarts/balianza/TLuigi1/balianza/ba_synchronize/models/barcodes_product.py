# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Objeto para relación de integración SIA-ODOO de multiples codigos de barra relacionados a un producto.
class BarcodesProduct (models.Model):

    _name='barcodes.product'
    _description = 'Multiple barcodes related to product'

    
    name = fields.Char(string='Codigo Barras', required=True)
    unit_of_measure_id = fields.Many2one('uom.uom',string='Unidad de medida', required=True)
    product_id = fields.Many2one('product.template',string='Producto', required=True)
