# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Log para modificación de precios, cada actualización de precios quedará registrada en este objeto.
class ChangePrices(models.Model):

    _name='change.prices'
    _description = 'Log for change prices'

    
    name = fields.Char(string='Motivo cambio', required=True)
    user_id =fields.Many2one('res.users',string="Usuario")
    change_date = fields.Datetime(string="Fecha y hora")
    pricelist_id = fields.Many2one('product.pricelist', string="Lista de precios")
    product_id = fields.Many2one('product.template', string="Producto")
    type_update = fields.Selection([('create', 'Creación'), ('update', 'Actualización')], string="Tipo de modificación", required=True)
    price_new  = fields.Float(string="Precio nuevo")
    discount_new = fields.Float(string="Descuento nuevo")
    price_old = fields.Float(string="Precio anterior")
    discount_old = fields.Float(string="Descuento anterior")
    inv_available = fields.Float(string="Inventario disponible")
    packing_quantity = fields.Float(string="Cajas")
    packing_unit_id = fields.Many2one('uom.uom', string="Unidad", readonly=True)
    quantity_unit = fields.Float(string="Unidades")
    unit_id = fields.Many2one('uom.uom', string="Unidad", readonly=True)

