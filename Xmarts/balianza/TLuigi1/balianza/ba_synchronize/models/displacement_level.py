# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Objeto creado para relación del nivel de desplazamiento de los productos, sincronizado desde SIA.
class DisplacementLevel(models.Model):

    _name='displacement.level'
    _description = 'Level displacement for products'

    
    name = fields.Char(string='Descripción', required=True)
    level = fields.Selection([('high', 'A'), ('half', 'B'), ('low', 'C')], string="Nivel desplazamiento", required=True)
    percent_from = fields.Float(string="Porcentaje desde")
    percent_to = fields.Float(string="Porcentaje a")