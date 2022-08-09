# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Codigo para parametrización de almacenes permitidos y relacionados a serie y puntos de venta.
class ParamsSeriePointSaleWarehouse(models.Model):

    _name='params.serie.point.sale.warehouse'
    _description = 'Parameters for point of sale and warehouse'
    
    name = fields.Char(string='Descripción', compute='get_name')
    company_id = fields.Many2one('res.company',string="Compañia", required=True)
    serie_id = fields.Many2one('ir.sequence', string="Serie", required=True)
    point_sale_id = fields.Many2one('pos.config', string="Punto de venta", required=True)
    warehouse_ids = fields.One2many('warehouse.related','params_id', string="Almacenes relacionados", required=True)
    number_warehouse_actives = fields.Integer(string="Número almacenes activos", compute='get_number_warehouses_actives')

    def name_get(self):
        result = []
        for params in self:
            result.append((params.id, "%s - %s - %s" % (params.company_id.company_code,params.serie_id.serie,params.point_sale_id.code)))
        return result

    @api.depends('name')
    def get_name(self):
        for params in self:
            params.name = str(params.company_id.company_code) + " - " + str(params.serie_id.serie) + " - " + str(params.point_sale_id.code)


    @api.depends('number_warehouse_actives')
    def get_number_warehouses_actives(self):
        for params in self:
            params.number_warehouse_actives = len(params.env['warehouse.related'].search([('params_id','=',params.id),('status','=',True)]))

class WarehouseRelated(models.Model):

    _name='warehouse.related'
    _description = 'Warehouses related to serie and ptv'
    _order = "sequence asc"
    
    params_id = fields.Many2one('params.serie.point.sale.warehouse',string='Parametro')
    warehouse_id = fields.Many2one('stock.location', string="Almacen", required=True)
    warehouse_code = fields.Char(string="Codigo Almacen", related='warehouse_id.code')
    sequence = fields.Integer(string="Secuencia", related='warehouse_id.sequence')
    status = fields.Boolean(string="Estatus",store=True)
    


    

