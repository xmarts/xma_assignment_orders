# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone

#Codigo para integración SIA-ODOO personalizada, parametrización de EndPoint de API para ejecución de sincronización inicial.
class BaSynchronize (models.Model):

    _name='ba.synchronize'
    _description = 'synchronize data'

    
    name = fields.Char(string='Base de datos', required=True)
    ip = fields.Char(string='Dirección del Servidor', required=True)
    user = fields.Char(string='Usuario', required=True)
    port = fields.Integer(string='Puerto', required=True)
    password = fields.Char(string='Contraseña', required=True)
    clients_synchronized = fields.Boolean(string="Clientes sincronizados por primera vez?", default=False, store=True)
    users_synchronized = fields.Boolean(string="Usuarios sincronizados por primera vez?", default=False, store=True)
    suppliers_synchronized = fields.Boolean(string="Proveedores sincronizados por primera vez?", default=False, store=True)
    business_synchronized = fields.Boolean(string="Empresas sincronizadas por primera vez?", default=False, store=True)
    kardex_synchronized = fields.Boolean(string="Kardex sincronizado por primera vez?", default=False, store=True)
    stock_synchronized = fields.Boolean(string="Almacenes sincronizados por primera vez?", default=False, store=True)
    productos_synchronized = fields.Boolean(string="Productos sincronizados por primera vez?", default=False, store=True)
    sale_order_synchronized = fields.Boolean(string="Pedidos sincronizados por primera vez?", default=False, store=True)
    price_list_synchronized = fields.Boolean(string="Listas de precios sincronizadas por primera vez?", default=False, store=True)
    employes_synchronized = fields.Boolean(string="Empleados sincronizadas por primera vez?", default=False, store=True)
    series_synchronized = fields.Boolean(string="Series sincronizadas por primera vez?", default=False, store=True)
    params_stock_serie_ptv_synchronized = fields.Boolean(string="Parametros almacen-serie-ptv sincronizados por primera vez?",default=False,store=True)
    point_of_sale_synchronized = fields.Boolean(string="Puntos de venta sincronizados por primera vez?",default=False,store=True)
    barcodes_synchronized = fields.Boolean(string="Codigos de barras sincronizados por primera vez?",default=False,store=True)
    logistics_footprint_synchronized = fields.Boolean(string="Huella logistica sincronizada por primera vez?",default=False,store=True)
    postal_code_synchronized = fields.Boolean(string="Codigos postales sincronizados por primera vez?",default=False,store=True)

    integration_parameters_ids = fields.One2many('ba.parametros.integracion.sia.odoo', 'synchronize_related_id', string="Parametros de sincronización")


    def api_get_token(self):
        #print("Ingresa a api_get_token")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','login')],limit=1)
        if api:
            api_url = api.url_api
            try:
                response = requests.get(api_url,auth=HTTPBasicAuth(api.user_api, api.password_api))
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url)))
            if response.status_code == 200:
                token = str(response.json().get('token'))
                return token
            else:
                raise ValidationError(_('Error conexión con API: '+ api_url))
        else:
            raise ValidationError(_('Error no se encontraton los parametros de configuración'))

    def action_synchronize_all(self):
        self.action_synchronize_business()
        self.action_synchronize_users()
        self.action_synchronize_series()
        self.action_synchronize_products()
        self.action_synchronize_price_list()
        self.action_synchronize_clients()
        self.action_synchronize_suppliers()
        self.action_synchronize_stock()
        self.action_synchronize_kardex()
        self.action_synchronize_sale_order()
        
        
    def action_synchronize_users(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','usuarios')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de usuarios SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"res.users"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API usuarios'))
            else:
                #print ("Esto es response",response.json())
                self.users_synchronized = True
        else:
            raise ValidationError("No se encontró el API usuarios")

    def action_synchronize_clients(self):
        if self.price_list_synchronized == False:
            raise ValidationError("Primero debe sincronizar las listas de precios")
        if self.postal_code_synchronized == False:
            raise ValidationError("Primero debe sincronizar los codigos postales")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','clientes')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de clientes SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"res.partner"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API clientes'))
            else:
                #print ("Esto es response",response.json())
                self.clients_synchronized = True
        else:
            raise ValidationError("No se encontró el API clientes")


    def action_synchronize_suppliers(self):
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','proveedores')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de proveedores SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"res.partner"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API proveedores'))
            else:
                #print ("Esto es response",response.json())
                self.suppliers_synchronized = True
        else:
            raise ValidationError("No se encontró el API proveedores")


    def action_synchronize_business(self):
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','empresas')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de empresas SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"res.company"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API empresas'))
            else:
                #print ("Esto es response",response.json())
                self.business_synchronized = True
        else:
            raise ValidationError("No se encontró el API empresas")

    def action_synchronize_products(self):
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','productos')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de productos SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"product.template"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API productos'))
            else:
                #print ("Esto es response",response.json())
                self.productos_synchronized = True
        else:
            raise ValidationError("No se encontró el API productos")


    def action_synchronize_stock(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")

        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','almacenes')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de almacenes SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"stock"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API almacenes'))
            else:
                #print ("Esto es response",response.json())
                self.stock_synchronized = True
        else:
            raise ValidationError("No se encontró el API almacenes")

    def action_synchronize_kardex(self):
        if self.stock_synchronized == False:
            raise ValidationError("Primero debe sincronizar almacenes")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','allkardex')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de kardex SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"stock.quant"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API allkardex'))
            else:
                #print ("Esto es response",response.json())
                self.kardex_synchronized = True
        else:
            raise ValidationError("No se encontró el API allkardex")

    def action_synchronize_sale_order(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")
        if self.clients_synchronized == False:
            raise ValidationError("Primero debe sincronizar clientes")
        if self.productos_synchronized == False:
            raise ValidationError("Primero debe sincronizar productos")
        if self.stock_synchronized == False:
            raise ValidationError("Primero debe sincronizar almacenes")
        if self.kardex_synchronized == False:
            raise ValidationError("Primero debe sincronizar Kardex")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','pedidos')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de pedidos SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"sale.order"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API pedidos'))
            else:
                #print ("Esto es response",response.json())
                self.sale_order_synchronized = True
        else:
            raise ValidationError("No se encontró el API pedidos")


    def action_synchronize_series(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")
        if self.point_of_sale_synchronized == False:
            raise ValidationError("Primero debe sincronizar puntos de venta")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','series')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de series SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"ir.sequence"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API series'))
            else:
                #print ("Esto es response",response.json())
                self.series_synchronized = True
        else:
            raise ValidationError("No se encontró el API series")


    def action_synchronize_price_list(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")
        #if self.series_synchronized == False:
        #    raise ValidationError("Primero debe sincronizar series")
        if self.productos_synchronized == False:
            raise ValidationError("Primero debe sincronizar productos")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','listaprecios')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de listas de precios SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"product.pricelist.item"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API listaprecios'))
            else:
                #print ("Esto es response",response.json())
                self.price_list_synchronized = True
        else:
            raise ValidationError("No se encontró el API listaprecios")


    def action_synchronize_employes(self):
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','empleados')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de empleados SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"hr.employee"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API empleados'))
            else:
                #print ("Esto es response",response.json())
                self.employes_synchronized = True
        else:
            raise ValidationError("No se encontró el API empleados")

    def action_synchronize_params_stock_ptv(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")
        if self.series_synchronized == False:
            raise ValidationError("Primero debe sincronizar series")
        if self.point_of_sale_synchronized == False:
            raise ValidationError("Primero debe sincronizar puntos de venta")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','parametros_almacen_serie_pvt')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de parametros almacen-serie-ptv SIA-ODOO",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"params.serie.point.sale.warehouse"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API parametros_almacen_serie_pvt'))
            else:
                #print ("Esto es response",response.json())
                self.params_stock_serie_ptv_synchronized = True
        else:
            raise ValidationError("No se encontró el API parametros_almacen_serie_pvt")

    def action_synchronize_point_of_sale(self):
        if self.business_synchronized == False:
            raise ValidationError("Primero debe sincronizar empresas")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','punto_venta')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de puntos de venta",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"pos.config"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API punto_venta'))
            else:
                #print ("Esto es response",response.json())
                self.point_of_sale_synchronized = True
        else:
            raise ValidationError("No se encontró el API punto_venta")

    def action_synchronize_barcodes(self):
        if self.productos_synchronized == False:
            raise ValidationError("Primero debe sincronizar productos")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','codigos_barras')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de codigos de barras",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"barcodes.product"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API codigos_barras'))
            else:
                #print ("Esto es response",response.json())
                self.barcodes_synchronized = True
        else:
            raise ValidationError("No se encontró el API codigos_barras")

    def action_synchronize_logistics_footprint(self):
        if self.productos_synchronized == False:
            raise ValidationError("Primero debe sincronizar productos")
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','huella_logistica')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de huella logística",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"product.template"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API huella_logistica'))
            else:
                #print ("Esto es response",response.json())
                self.logistics_footprint_synchronized = True
        else:
            raise ValidationError("No se encontró el API huella_logistica")
        
    def action_synchronize_postal_code(self):
        token = ""
        api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','codigo_pos')])
        if api:
            #print ("Esto es API antes de token",api)
            api_url_company = api.url_api
            token = self.env['ba.synchronize'].api_get_token()

            headers = {
                'Accept': 'registy/json',
                'x-access-tokens': token,
                'Content-Type': 'application/json'
                }
            information = {
                "description":"Sincronización de codigos postales",
                "type":"Sincronización inicial",
                "from_system":"SIA",
                "user_id":self.env.user.name,
                "company":self.env.user.company_id.company_code,
                "model":"postal.code"
                }
            
            information_json = json.dumps(information)
            try:
                response = requests.post(api_url_company, headers=headers, data=information_json)
            except:
                raise ValidationError(_('Error timeout a: '+ (api_url_company)))

            if response.json() == []:
                raise ValidationError(_('Error de respuesta con la API codigo_pos'))
            else:
                #print ("Esto es response",response.json())
                self.postal_code_synchronized = True
        else:
            raise ValidationError("No se encontró el API codigo_pos")

class BaParametrosIntegracionSiaOdoo(models.Model):

    _name='ba.parametros.integracion.sia.odoo'
    _description = 'Parametros integracion SIA-ODOO'

    code_api = fields.Char(string='Codigo API', required=True)
    url_api = fields.Char(string='URL API', required=True)
    user_api = fields.Char(string='Usuario')
    password_api = fields.Char(string='Password')
    description_api = fields.Char(string='Descripción')
    registration_date = fields.Datetime(string='Fecha', default=datetime.now(),required=True)
    synchronize = fields.Boolean(string='Sincronizar', default=True)
    synchronize_related_id = fields.Many2one('ba.synchronize', string="Sincronización relacionada")




        


class BaParametrosLimitacion(models.Model):

    _name='ba.paramametros.limitacion'
    _description = 'Parametro para limitación de registros'

    
    name = fields.Selection([('general','General')], string="Tipo de parametrización", required=True, default="general")
    date_synchronize = fields.Date(string="Sincronización desde")
    