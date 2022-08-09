# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Objeto para guardar impuestos desglozados de ordenes de compras.
class PurchaseLineTax (models.Model):

    _name='purchase.line.tax'
    _description = 'Data of taxes related to purchase'

    name = fields.Char(string="Nombre impuesto", readonly=True) 
    monto_base = fields.Char(string="Monto base", readonly=True)
    total_impuesto = fields.Char(string="Total Impuesto", readonly=True) 
    purchase_related_id=fields.Many2one('purchase.order', string="Compra relacionada",  index=True,  ondelete='cascade')

