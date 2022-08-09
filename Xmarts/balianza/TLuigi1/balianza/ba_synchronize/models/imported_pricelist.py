# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import datetime
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import itertools
from operator import itemgetter
import operator
import odoo
import base64
from os.path import join
import os
import time

#Añadido para complementar actualización de precios por medio de layout, todos los registros que se importen se podrán visualizar en estos objetos para validación.
class ImportPricelistItem(models.Model):
    _name = 'imported.pricelist.item'

    pricelist_id = fields.Many2one('product.pricelist',string='pricelist', store=True)
    pricelist_id_name = fields.Char(string='Listas de precios', related="pricelist_id.name", store =True)
    pricelist_id_code = fields.Char(string='Listas de precios', related="pricelist_id.code", store =True)

    product_id = fields.Many2one('product.template',string="Producto",store=True, required=True)
    price_unidad = fields.Float(string="Precio empaque",store=True, required=True)
    percent_discount = fields.Float(string="Porcentaje de descuento",store=True, required=True)
    price_sub_unidad = fields.Float(string="Precio por unidad con descuento")

    
    price_old = fields.Float(string="Precio actual",store=True,compute='onchange_price_percent_unidad')
    discount_old = fields.Float(string="Porcentaje descuento actual",store=True,compute='onchange_price_percent_unidad')
    price_sub_unidad_old = fields.Float(string="Precio por unidad con descuento actual",store=True,compute='onchange_price_percent_unidad')
    update_pricelist_item_id = fields.Many2one('imported.pricelist', store=True)
    alert_message = fields.Char(string='Estatus',compute='onchange_price_percent_unidad')
    diference_price_limit = fields.Selection([('right','Correcto'),('alert','Alerta'),('equal','Igual')], string="Diferencia limite", store=True,compute='onchange_price_percent_unidad')

    @api.onchange('price_unidad','percent_discount')
    def onchange_price_percent_unidad(self):
        for registro in self:
            if registro.percent_discount < 0:
                raise ValidationError("No se puede agregar un descuento negativo.")
            if registro.percent_discount > 100:
                raise ValidationError("No se puede agregar un descuento mayor al 100%")
            if registro.price_unidad < 0:
                raise ValidationError("No se puede agregar un precio negativo.")
            if registro.price_unidad:
                registro.price_sub_unidad = (registro.price_unidad * ((100-registro.percent_discount)/100)) / registro.product_id.quantity_uom
            if registro.price_unidad == 0:
                registro.percent_discount = 0
                registro.price_sub_unidad = 0
            if registro.price_unidad > 0:
                parametros = registro.env['params.log.comercial'].search([('company_id','=',False)])
                pricelist_item = registro.env['product.pricelist.item'].search([('product_tmpl_id','=',registro.product_id.id),('pricelist_id','=',registro.pricelist_id.id)])
                pricelist_item_fixed_price = pricelist_item.fixed_price
                if pricelist_item.limit_update_price == True:
                    if pricelist_item.type_limit == 'amount':
                        cantidad_maxima_aumento = pricelist_item.amount_update_limit_up
                        cantidad_maxima_disminucion = pricelist_item.amount_update_limit_down
                        if registro.price_sub_unidad > pricelist_item_fixed_price:
                            diferencia = registro.price_sub_unidad - pricelist_item_fixed_price
                            if diferencia <= cantidad_maxima_aumento:
                                registro.diference_price_limit = 'right'
                                registro.alert_message = "OK"
                            else:
                                registro.diference_price_limit = 'alert'
                                registro.alert_message = "Se está exediendo el monto máximo de aumento establecido en la lista de precio del producto, el valor máximo de aumento es de $"+ str(cantidad_maxima_aumento)

                        elif registro.price_sub_unidad < pricelist_item_fixed_price:
                            diferencia = pricelist_item_fixed_price - registro.price_sub_unidad
                            if diferencia <= cantidad_maxima_disminucion:
                                registro.diference_price_limit = 'right'
                                registro.alert_message = "OK"
                            else:
                                registro.diference_price_limit = 'alert'
                                registro.alert_message = "Se está exediendo el monto máximo de disminución establecido en la lista de precio del producto, el valor máximo de disminución es de $"+ str(cantidad_maxima_disminucion)

                        else:
                            registro.diference_price_limit = 'equal'
                            registro.alert_message = "El nuevo valor es igual al anterior"


                    if pricelist_item.type_limit == 'percent':
                        porcentaje_maximo_aumento = pricelist_item.percent_update_limit_up
                        porcentaje_maximo_dismininucion = pricelist_item.percent_update_limit_down
                        diferencia = registro.price_sub_unidad - pricelist_item_fixed_price
                        if diferencia > 0:
                            diferencia_porcentaje = (diferencia/pricelist_item_fixed_price) * 100
                            if diferencia_porcentaje <= porcentaje_maximo_aumento:
                                registro.diference_price_limit = 'right'
                                registro.alert_message = "OK"
                            else:
                                registro.diference_price_limit = 'alert'
                                registro.alert_message = "Se está exediendo el porcentaje máximo de aumento establecido en la lista de precio del producto, el porcentaje máximo de aumento es del "+ str(porcentaje_maximo_aumento) + "%"

                        elif diferencia < 0:
                            diferencia_porcentaje = (abs(diferencia)/pricelist_item_fixed_price) * 100
                            if diferencia_porcentaje <= porcentaje_maximo_dismininucion:
                                registro.diference_price_limit = 'right'
                                registro.alert_message = "OK"
                            else:
                                registro.diference_price_limit = 'alert'
                                registro.alert_message = "Se está exediendo el porcentaje máximo de disminución establecido en la lista de precio del producto, el porcentaje máximo de disminución es del "+ str(porcentaje_maximo_dismininucion) + "%"
                            
                        else:
                            registro.diference_price_limit = 'equal'
                            registro.alert_message = "El nuevo valor es igual al anterior"

                elif parametros:
                    if len(parametros) >= 2:
                        raise ValidationError('No puede existir más de un registro compartido entre compañias creado en Parametros Comerciales')
                    else:
                        porcentaje_maximo_aumento = parametros.percent_update_limit_up
                        porcentaje_maximo_dismininucion = parametros.percent_update_limit_down
                        diferencia = registro.price_sub_unidad - pricelist_item_fixed_price
                        if diferencia > 0:
                            diferencia_porcentaje = (diferencia/pricelist_item_fixed_price) * 100
                            if diferencia_porcentaje <= porcentaje_maximo_aumento:
                                registro.diference_price_limit = 'right'
                                registro.alert_message = "OK"
                            else:
                                registro.diference_price_limit = 'alert'
                                registro.alert_message = "Se está exediendo el porcentaje máximo de aumento establecido en los parametros comerciales, el porcentaje máximo de aumento es del "+ str(porcentaje_maximo_aumento) + "%"

                        elif diferencia < 0:
                            diferencia_porcentaje = (abs(diferencia)/pricelist_item_fixed_price) * 100
                            if diferencia_porcentaje <= porcentaje_maximo_dismininucion:
                                registro.diference_price_limit = 'right'
                                registro.alert_message = "OK"
                            else:
                                registro.diference_price_limit = 'alert'
                                registro.alert_message = "Se está exediendo el porcentaje máximo de disminución establecido en los parametros comerciales, el porcentaje máximo de disminución es del "+ str(porcentaje_maximo_dismininucion) + "%"
                            
                        else:
                            registro.diference_price_limit = 'equal'
                            registro.alert_message = "El nuevo valor es igual al anterior"

                else:
                    registro.env.user.notify_danger(message='No se encontraron parametros establecidos de "limite de aumento o disminución de precios", se buscó en la lista de precios del producto y en los parametros Comerciales, considere agregar alguno de estos parametros para evitar errores en la actualización de precios.' )

            

class ImportPricelist(models.Model):
    _name = 'imported.pricelist'

    name = fields.Char(string="Motivo cambio de precio", store=True, required=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", store=True)
    user_id = fields.Many2one('res.users',string="Usuario")
    pricelist_ids = fields.One2many('imported.pricelist.item','update_pricelist_item_id',string='Lista de precios', store=True)
    status = fields.Selection([('draft','Borrador'),('done','Realizado')], string="Estatus",default='draft', store=True)

    def process_update_pricelist(self):
        #print ("Ingresa a la función",self.env.user.company_id)
        for pricelist in self.pricelist_ids:
            registro = self.env['product.pricelist.item'].search([('product_tmpl_id','=',self.product_id.id),('pricelist_id','=',pricelist.pricelist_id.id)])
            
            if registro:
                vals = {
                'name':self.name,
                'user_id':self.env.user.id,
                'change_date':datetime.datetime.now(),
                'pricelist_id':pricelist.pricelist_id.id,
                'product_id':pricelist.product_id.id,
                'type_update':'update',
                'price_new':pricelist.price_unidad,
                'discount_new':pricelist.percent_discount,
                'price_old':registro.price_unidad,
                'discount_old':registro.percent_discount_unidad,
                }
                self.env['change.prices'].sudo().create(vals)
                registro.write({'price_unidad':self.price_unidad,'percent_discount_unidad':self.percent_discount,'fixed_price':self.price_sub_unidad})

            else:
                vals = {
                'name':self.name,
                'user_id':self.env.user.id,
                'change_date':datetime.datetime.now(),
                'pricelist_id':pricelist.pricelist_id.id,
                'product_id':pricelist.product_id.id,
                'type_update':'create',
                'price_new':pricelist.price_unidad,
                'discount_new':pricelist.percent_discount,
                'price_old':0,
                'discount_old':0,
                }
                values = {
                'product_tmpl_id':pricelist.product_id.id,
                'product_id': False,
                'categ_id':False,
                'min_quantity':0,
                'applied_on':'1_product',
                'base':'list_price',
                'base_pricelist_id':False,
                'pricelist_id':pricelist.pricelist_id.id,
                'price_surcharge':0,
                'price_discount':0,
                'price_round':0,
                'price_min_margin':0,
                'price_max_margin':0,
                'company_id':False,
                'currency_id':self.currency_id.id,
                'active':True,
                'date_start':False,
                'date_end':False,
                'compute_price':'fixed',
                'fixed_price':pricelist.price_sub_unidad,
                'percent_price':0,
                'price_unidad':pricelist.price_unidad,
                'percent_discount_unidad':pricelist.percent_discount,
                }
                self.env['change.prices'].sudo().create(vals)
                self.env['product.pricelist.item'].create(values)

        self.write({'status':'done'})

