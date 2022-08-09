# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Parametrización para restriccíón en actualización de precios.
class ParamsLogComercial(models.Model):

    _name='params.log.comercial'
    _description = 'Parameters for log comercial'

    
    name = fields.Char(string='Descripción', compute='get_name')
    company_id = fields.Many2one('res.company',string="Compañia" )
    point_sale_id = fields.Many2one('pos.config', string="Punto de venta")
    percent_update_limit_up =  fields.Integer(string="Porcentaje máximo aumento de precio",store=True,copy=False)
    percent_update_limit_down =  fields.Integer(string="Porcentaje máximo disminución de precio",store=True,copy=False)

    @api.depends('name')
    def get_name(self):
        for params in self:
            params.name = str(params.company_id.company_code) + " - " + str(params.point_sale_id.code)
            

    
            
