# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2013-Present Acespritech Solutions Pvt. Ltd.
#     (<http://acespritech.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models, api, _
import base64
import datetime
import time
import xlrd
import tempfile
import binascii
from xml.dom import minidom
from odoo.exceptions import UserError, AccessError
from odoo.exceptions import ValidationError


class cfs_import_wizard(models.TransientModel):
    _name = 'cfs.import.wizard'

    file = fields.Binary(string="Archivo", filters='*.xls')

    def fetch_invoice_data(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xls")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet_names = workbook.sheet_names()
        worksheet = workbook.sheet_by_name(sheet_names[0])
        renglon = 0
        motivo = ""
        contador = 0
        for rownum in range(worksheet.nrows):
            renglon = renglon + 1
            if rownum != 0:
                print ("esto es rownum ", rownum)
                row_val = worksheet.row_values(rownum)
                codigo_producto = str(row_val[1])
                product_id = self.env['product.template'].search([('default_code','=',codigo_producto)])
                if not row_val[0] != '':
                    raise ValidationError("No se encontró el motivo de cambio " + " en la columna "  + str(rownum + 1) )
                if not product_id:
                    raise ValidationError("No se encontró producto en base al Codigo Producto proporcionado: " + str(row_val[1]) + " en la columna "  + str(rownum + 1))
                if float(row_val[4]) < 0:
                    raise ValidationError("No se puede agregar un descuento negativo valor encontrado: " + str(row_val[4]) + " en la columna "  + str(rownum + 1))
                if float(row_val[4]) > 100:
                    raise ValidationError("No se puede agregar un descuento mayor al 100% valor encontrado: " + str(row_val[4]) + " en la columna "  + str(rownum + 1))
                if float(row_val[3]) < 0:
                    raise ValidationError("No se puede agregar un precio negativo valor encontrado: " + str(row_val[3]) + " en la columna "  + str(rownum + 1))
                

                print ("Esto es motivo",motivo)
                if motivo != str(row_val[0]):
                    if ',' in str(row_val[2]) and row_val[1] != '':
                        pricelist_ids = list(str(row_val[2]).split(","))
                        print ("Ingresa al primer if",pricelist_ids)
                        flag = False
                        for pricelist in pricelist_ids:
                            print ("Pasó al for esto es pricelist",pricelist)
                            pricelist_id = self.env['product.pricelist'].search([('code','=',str(pricelist))])
                            if not pricelist_id:
                                raise ValidationError("No se encontró lista de precios en base al codigo proporcionado: " + str(pricelist) + " en la columna "  + str(rownum + 1))
                            registro_id = self.env['product.pricelist.item'].search([('product_tmpl_id','=',product_id.id),('pricelist_id','=',pricelist_id.id)])
                            
                            if registro_id:
                                if flag == False:
                                    vals = {
                                    'name':str(row_val[0]),
                                    'user_id':self.env.user.id,
                                    'currency_id':self.env.user.company_id.currency_id.id,
                                    'status':'draft'
                                    }
                                    imported_id = self.env['imported.pricelist'].sudo().create(vals)
                                    contador = contador + 1
                                    flag = True

                                price_sub_unidad = (row_val[3] * ((100-row_val[4])/100)) / product_id.quantity_uom
                                values = {
                                'pricelist_id':pricelist_id.id,
                                'product_id':product_id.id,
                                'price_unidad':row_val[3],
                                'percent_discount':row_val[4],
                                'price_sub_unidad':price_sub_unidad,
                                'update_pricelist_item_id':imported_id.id,
                                }
                                imported_item_id = self.env['imported.pricelist.item'].sudo().create(values)
                                imported_item_id.onchange_price_percent_unidad()
                    elif ',' not in str(row_val[2]) and row_val[1] != '':
                        print ("Ingresó al elif",row_val[2])
                        pricelist_id = self.env['product.pricelist'].search([('code','=',str(row_val[2]))])
                        if not pricelist_id:
                            raise ValidationError("No se encontró lista de precios en base al codigo proporcionado: " + str(row_val[2]) + " en la columna "  + str(rownum + 1) )
                        registro_id = self.env['product.pricelist.item'].search([('product_tmpl_id','=',product_id.id),('pricelist_id','=',pricelist_id.id)])
                        
                        if registro_id:
                            vals = {
                            'name':str(row_val[0]),
                            'user_id':self.env.user.id,
                            'currency_id':self.env.user.company_id.currency_id.id,
                            'status':'draft'
                            }
                            print ("Pasó a actualizar",pricelist_id.name)
                            imported_id = self.env['imported.pricelist'].sudo().create(vals)
                            contador = contador + 1
                            price_sub_unidad = (row_val[3] * ((100-row_val[4])/100)) / product_id.quantity_uom
                            values = {
                            'pricelist_id':pricelist_id.id,
                            'product_id':product_id.id,
                            'price_unidad':row_val[3],
                            'percent_discount':row_val[4],
                            'price_sub_unidad':price_sub_unidad,
                            'update_pricelist_item_id':imported_id.id,
                            }
                            imported_item_id = self.env['imported.pricelist.item'].sudo().create(values)
                            imported_item_id.onchange_price_percent_unidad()
                else:
                    if ',' in str(row_val[2]) and row_val[1] != '':
                        pricelist_ids = list(str(row_val[2]).split(","))
                        print ("Ingresa al primer if",pricelist_ids)
                        for pricelist in pricelist_ids:
                            print ("Pasó al for esto es pricelist",pricelist)
                            pricelist_id = self.env['product.pricelist'].search([('code','=',str(pricelist))])
                            if not pricelist_id:
                                raise ValidationError("No se encontró lista de precios en base al codigo proporcionado: " + str(pricelist) + " en la columna "  + str(rownum + 1))
                            registro_id = self.env['product.pricelist.item'].search([('product_tmpl_id','=',product_id.id),('pricelist_id','=',pricelist_id.id)])
                            
                            if registro_id:

                                print ("Pasó a actualizar",pricelist_id.name)
                                price_sub_unidad = (row_val[3] * ((100-row_val[4])/100)) / product_id.quantity_uom
                                values = {
                                'pricelist_id':pricelist_id.id,
                                'product_id':product_id.id,
                                'price_unidad':row_val[3],
                                'percent_discount':row_val[4],
                                'price_sub_unidad':price_sub_unidad,
                                'update_pricelist_item_id':imported_id.id,
                                }
                                imported_item_id = self.env['imported.pricelist.item'].sudo().create(values)
                                imported_item_id.onchange_price_percent_unidad()
                    
                    elif ',' not in str(row_val[2]) and row_val[1] != '':
                        print ("Ingresó al elif",row_val[2])
                        pricelist_id = self.env['product.pricelist'].search([('code','=',str(row_val[2]))])
                        if not pricelist_id:
                            raise ValidationError("No se encontró lista de precios en base al codigo proporcionado: " + str(row_val[2]) + " en la columna "  + str(rownum + 1) )
                        registro_id = self.env['product.pricelist.item'].search([('product_tmpl_id','=',product_id.id),('pricelist_id','=',pricelist_id.id)])
                        
                        if registro_id:
                            print ("Pasó a actualizar",pricelist_id.name)
                            price_sub_unidad = (row_val[3] * ((100-row_val[4])/100)) / product_id.quantity_uom
                            values = {
                            'pricelist_id':pricelist_id.id,
                            'product_id':product_id.id,
                            'price_unidad':row_val[3],
                            'percent_discount':row_val[4],
                            'price_sub_unidad':price_sub_unidad,
                            'update_pricelist_item_id':imported_id.id,
                            }
                            imported_item_id = self.env['imported.pricelist.item'].sudo().create(values)
                            imported_item_id.onchange_price_percent_unidad()

                motivo = str(row_val[0])
        
        if contador ==1:
            view = self.env.ref('ba_synchronize.view_imported_pricelist_form')
            return {
                'name': _('Registro importado'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                #'res_model': 'cfs.log',
                'res_model': 'imported.pricelist',
                'views': [(view.id, 'list')],
                'view_id': view.id,
                'target': 'current',
                'res_id': imported_id.id,
                'context': self.env.context,
            }

        if contador >=2:
            return {
               'name': _('Registros importados para actualizar lista de precios'),
               'type': 'ir.actions.act_window',
               'res_model': 'imported.pricelist',
               'view_type': 'form',
               'view_mode': 'tree,form',
            }
