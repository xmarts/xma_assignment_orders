# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import requests
import json, ast
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pytz import timezone
from odoo.tools.translate import _
from lxml import etree
#Añadido para complementar integración SIA-ODOO en clientes, relación a multiples tablas de SIA, integración al dar alta de cliente.
class ResPartner(models.Model):

    _inherit='res.partner'

    client_code = fields.Char(string="Codigo cliente", store=True, readonly=True)
    client_created = fields.Boolean(string="Cliente creado", default=False, store=True, readonly=True)
    from_sia = fields.Boolean(string="Creado desde SIA?", store=True, readonly=True)
    is_employee = fields.Boolean(string="Es empleado?",store=True, default=False)
    employee_code = fields.Char(string="Codigo empleado",store=True)
    department_id = fields.Many2one('hr.department',string="Departamento",store=True)
    credit_limit = fields.Float(string="Limite de credito")
    credit_days = fields.Float(string="Dias de credito")
    discount = fields.Float(string="Descuento")
    point_of_sale = fields.Many2one('pos.config',string="Punto de venta")
    start_validity = fields.Datetime(string="Vigencia inicial")
    end_validity = fields.Datetime(string="Vigencia final")
    authorize = fields.Boolean(string="Autoriza")
    zip = fields.Char(change_default=True, required=True)
    colony_id = fields.Many2one('postal.code')

    def _fields_view_get_address(self, arch):
        # consider the country of the user, not the country of the partner we want to display
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        if address_view_id and not self._context.get('no_address_format') and (not address_view_id.model or address_view_id.model == self._name):
            #render the partner address accordingly to address_view_id
            doc = etree.fromstring(arch)
            for address_node in doc.xpath("//div[hasclass('o_address_format')]"):
                Partner = self.env['res.partner'].with_context(no_address_format=True)
                sub_view = Partner.fields_view_get(
                    view_id=address_view_id.id, view_type='form', toolbar=False, submenu=False)
                sub_view_node = etree.fromstring(sub_view['arch'])
                #if the model is different than res.partner, there are chances that the view won't work
                #(e.g fields not present on the model). In that case we just return arch
                if self._name != 'res.partner':
                    try:
                        self.env['ir.ui.view'].postprocess_and_fields(sub_view_node, model=self._name)
                    except ValueError:
                        return arch
                address_node.getparent().replace(address_node, sub_view_node)
            arch = etree.tostring(doc, encoding='unicode')
        return arch

    @api.onchange('colony_id')
    def _onchange_colony_id(self):
        print ("Ingresa a _onchange_colony_id")
        if self.colony_id:
            codigo_postal = self.env['postal.code'].search([('id','=',self.colony_id.id)], limit=1)
            if codigo_postal:
                self.zip = codigo_postal.zipcode
                self.city_id = codigo_postal.city_id.id
                self.state_id = codigo_postal.state_id.id
                self.country_id = codigo_postal.country_id.id
                self.l10n_mx_edi_colony = codigo_postal.name

        elif not self.colony_id and not self.zip:
            self.zip = False
            self.city_id = False
            self.state_id = False
            self.country_id = False
            self.l10n_mx_edi_colony = False

        else:
            self.l10n_mx_edi_colony = False




    @api.onchange('zip')
    def _onchange_zip(self):
        print ("Ingresa a _onchange_zip")
        if self.zip:
            codigo_postal = self.env['postal.code'].search([('zipcode','=',self.zip)], limit=1)
            if codigo_postal:
                if self.colony_id.zipcode != codigo_postal.zipcode:
                    self.colony_id = False 
                self.city_id = codigo_postal.city_id.id
                self.state_id = codigo_postal.state_id.id
                self.country_id = codigo_postal.country_id.id

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.state_id = self.city_id.state_id.id
            self.country_id = self.city_id.country_id.id
        elif self._origin:
            self.city = False
            self.state_id = False
        else:
            self.city = False

    def _inverse_street_data(self):
        return

    @api.depends('street')
    def _compute_street_data(self):
        return
        
    #def name_get(self):
    #    name = [(partner.id, '%s - %s' % (partner.client_code,partner.name)) for partner in self]
    #    return name

    def name_get(self):
        result = []
        for partner in self:
            if partner.is_employee == True:
                result.append((partner.id, '%s - %s' % (partner.employee_code,partner.name)))
            elif partner.client_code != False:
                result.append((partner.id, '%s - %s' % (partner.client_code,partner.name)))
            else:
                result.append((partner.id, '%s' % (partner.name)))
        return result

    #Quitar restricción en validación de RFC para compatibilidad con SIA
    @api.model
    def check_vat(self):
        return
        #print("Ahora ingresa aqui")
        


    def write(self, vals):
        flag1 = 0
        if self.env.context:
            flag1 = 1

        flag = 0
        companys = self.env['res.company'].search([])
        for company in companys:
            if self.name == company.name:
                flag = 1

        if self.client_created == False and self.from_sia != True and flag==0 and flag1 == 1:
            if not self.env.context.get('binary_field_real_user'):
                token = ""
                api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','client')])
                if api.synchronize == True:
                    api_url_client = api.url_api
                    token = self.env['ba.synchronize'].api_get_token()

                    headers = {
                        'Accept': 'registy/json',
                        'x-access-tokens': token,
                        'Content-Type': 'application/json'
                        }
                    client_code = self.env['ir.sequence'].next_by_code('res.partner')

                    information = {
                        "description":"Creación cliente",
                        "type":"GUARDAR",
                        "from_system":"ODOO",
                        "id":self.id,
                        "name":self.name,
                        "street":self.street_name,
                        "street2":self.street2,
                        "zip":self.zip,
                        "phone":self.phone,
                        "mobile":self.mobile,
                        "email":self.email,
                        "client_code":client_code,
                        "company_type":self.company_type,
                        "user_id":self.env.user.name,
                        "company":self.env.user.company_id.company_code,
                        "model":"res.partner"
                        }

                    
                    information_json = json.dumps(information)
                    try:
                        response = requests.post(api_url_client, headers=headers, data=information_json)
                    except:
                        raise ValidationError(_('Error timeout a: '+ (api_url_client)))

                    if response.json() == []:
                        raise ValidationError(_('Error de conexión con la API clients'))
                    vals.update({'client_created':True,'client_code':client_code})

        res = super(ResPartner, self).write(vals)

        if self.client_created == True and self.from_sia != True and flag==0 or flag1 == 1 and flag==0:
                token = ""
                api = self.env['ba.parametros.integracion.sia.odoo'].search([('code_api','=','client')])

                if api.synchronize == True:
                    api_url_client = api.url_api
                    token = self.env['ba.synchronize'].api_get_token()

                    headers = {
                        'Accept': 'registy/json',
                        'x-access-tokens': token,
                        'Content-Type': 'application/json'
                        }
                    information = {
                        "description":"Editar cliente",
                        "type":"EDITAR",
                        "from_system":"ODOO",
                        "id":self.id,
                        "name":self.name,
                        "street":self.street_name,
                        "street2":self.street2,
                        "zip":self.zip,
                        "phone":self.phone,
                        "mobile":self.mobile,
                        "email":self.email,
                        "client_code":self.client_code,
                        "comment":self.comment,
                        "company_type":self.company_type,
                        "user_id":self.env.user.name,
                        "company":self.env.user.company_id.company_code,
                        "model":"res.partner"
                        }
                    
                    information_json = json.dumps(information)
                    try:
                        response = requests.post(api_url_client, headers=headers, data=information_json)
                    except:
                        raise ValidationError(_('Error timeout a: '+ (api_url_client)))

                    if response.json() == []:
                        raise ValidationError(_('Error de conexión con la API clients'))
        
        return res

    