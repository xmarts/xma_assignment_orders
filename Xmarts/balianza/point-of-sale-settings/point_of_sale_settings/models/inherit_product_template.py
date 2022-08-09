# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InheritProductTemplate(models.Model):
    _inherit = "product.template"

    scan_in_pos = fields.Boolean(string="Debe ser escaneado")

    @api.model
    def search_barcode(self, code):
        result = False
        uom_id = 0
        product_id = 0
        uom_name = ''
        barcodes = self.env['barcodes.product'].search([('name','=',str(code))], limit=1)
        if barcodes:
            result = True
            uom_id = barcodes.unit_of_measure_id.id
            uom_name = barcodes.unit_of_measure_id.name
            product_id = barcodes.product_id.id
        return {"res": result, 'uom_id': uom_id, 'uom_name': uom_name, 'product_id': product_id}
