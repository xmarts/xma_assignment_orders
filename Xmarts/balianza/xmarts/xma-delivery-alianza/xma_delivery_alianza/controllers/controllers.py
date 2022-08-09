
# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request, Response
from datetime import date

import logging
_logger = logging.getLogger(__name__)

class DeliveryAlianza(http.Controller):

    unauthorized = {
        "ok": False, 
        "msg": "Sin autorizacion", 
        "data": ""
    }
    
    error_500 = {
        "ok": False,  
        "msg": "Error: Se ha producido un error en la peticion", 
        "data": ""
    }
    
    @http.route('/api/login/', auth='public', method=['POST'], type='json', csrf_token=False)
    def login(self, **kw):
        res = request.env['hr.employee'].sudo()._login_app(json.loads(request.httprequest.data))
        if not res:
            return {"ok": False, "msg":"No coinciden los datos", "data": ""}
        return res

    @staticmethod
    def _validate_header():
        """ Header Validation """
        try:
            authorization = request.httprequest.headers.environ.get('HTTP_AUTHORIZATION')
            if authorization:
                res = request.env['hr.employee'].sudo().search([('token','=', authorization)])
                if res: return res
            return False
        except:
            return False

    @http.route('/api/motives/', auth='public', type='json', method=['POST'], csrf_token=False)
    def get_motives_cancellations(self, **kw):
        try:
            validate = self._validate_header()
            if not validate:
                return unauthorized
            return self._search_motives_cancellations()
        except:
            return error_500

    @staticmethod
    def _search_motives_cancellations():
        try:
            motives = request.env['pos.order.cancellations'].sudo().search([])
            data = [
                    {
                        'id': rec.id,
                        'name': rec.name
                    }
                for rec in motives
            ]
            return { "ok": True, "data": data, "msg": "" }
        except Exception as Error:
            return { "ok": False,"data": "", "msg": str(Error) }

    @http.route('/api/contacts/', auth='public', type='json', method=['POST'], csrf_token=False)
    def get_contacts(self, **kw):
        try:
            validate = self._validate_header()
            if not validate:
                return unauthorized
            return self._search_contacts()
        except:
            return error_500
        
    @staticmethod
    def _search_contacts():
        try:
            motives = request.env['res.partner'].sudo().search([])
            data = [
                    {
                        'id': rec.id,
                        'name': rec.name,
                        'phone': rec.phone,
                        'mobile': rec.mobile,
                        'email': rec.email,
                        'contact_address': rec.contact_address,
                        'latitude': rec.partner_latitude,
                        'longitude': rec.partner_longitude
                    }
                for rec in motives
            ]
            return { "ok": True, "data": data, "msg": "" }
        except Exception as Error:
            return { "ok": False,"data": "", "msg": str(Error) }
    
    @http.route('/api/sucursales/', auth='public', type='json', method=['POST'], csrf_token=False)
    def get_sucursales(self, **kw):
        try:
            validate = self._validate_header()
            if not validate:
                return unauthorized
            return self._search_sucursales()
        except:
            return error_500

    @staticmethod
    def _search_sucursales():
        try:
            sucursales = request.env['pos.config'].sudo().search([])
            data = [
                    {
                        'id': rec.id,
                        'name': rec.name,
                        'address': rec.contact_address_complete
                    }
                for rec in sucursales
            ]
            return { "ok": True, "data": data, "msg": "" }
        except Exception as Error:
            return { "ok": False,"data": "", "msg": str(Error) }

    @http.route('/api/metodos/', auth='public', type='json', method=['POST'], csrf_token=False)
    def get_payments_method(self, **kw):
        try:
            validate = self._validate_header()
            if not validate:
                return unauthorized
            return self._search_payments_method()
        except:
            return error_500

    @staticmethod
    def _search_payments_method():
        try:
            payment_method = request.env['pos.payment.method'].sudo().search([])
            data = [
                    {   
                        'id': rec.id,
                        'name': rec.name,
                    }
                for rec in payment_method
            ]
            return { "ok": True, "data": data, "msg": "" }
        except Exception as Error:
            return { "ok": False,"data": "", "msg": str(Error) }


    @http.route('/api/metodos_pos/', auth='public', type='json', method=['POST'], csrf_token=False)
    def get_payments_method_pos(self, **kw):
        try:
            validate = self._validate_header()
            if not validate:
                return unauthorized
            return self._search_payments_method_pos()
        except:
            return error_500

    @staticmethod
    def _search_payments_method_pos():
        try:
            payment_method_pos = request.env['pos.payment'].sudo().search([])
            data = [
                    {   
                        'id': rec.id,
                        'method': rec.payment_method_id.id,
                        'order_id': rec.pos_order_id.id,
                        'payment_date': rec.payment_date,
                        'amount': rec.amount
                    }
                for rec in payment_method_pos
            ]
            return { "ok": True, "data": data, "msg": "" }
        except Exception as Error:
            return { "ok": False,"data": "", "msg": str(Error) }
    
    @http.route('/api/ordenes/', auth='public', type='json', method=['POST'], csrf_token=False)
    def get_pos_orders(self, **kw):
        try:
            validate = self._validate_header()
            if not validate:
                return unauthorized
            return self._search_pos_order(validate)
        except:
            return error_500

    @staticmethod
    def _search_pos_order(delivery):
        try:
            orders = request.env['pos.payment'].sudo().search([
                ('repartidor', '=', delivery.id)
            ])
            data = [
                    {   
                        'serie': rec.serie_id.id,
                        'partner_id': rec.partner_id.id,
                        'email': rec.partner_id.email,
                        'state': rec.state,
                        'price_subtotal_inc': rec.price_subtotal_inc,
                        'amount_total': rec.amount_total,
                        'signature': rec.signature,
                        'date_order': rec.date_order,
                        'date_today': rec.date_today,
                        'cancellations_id': rec.order_cancellations_id.ids,
                        'client_name': rec.partner_id.name,
                        'phone': rec.partner_id.phonem,
                        'mobile': rec.partner_id.mobile,
                        'product_lines': rec.lines,
                        'payments': rec.payment_ids,
                        'sucursal': rec.config_id.name 
                    }
                for rec in orders
            ]
            return { "ok": True, "data": data, "msg": "" }
        except Exception as Error:
            return { "ok": False,"data": "", "msg": str(Error) }
