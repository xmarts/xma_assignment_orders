# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

#Codigo agregado para control por lineas de movimientos de entrada y salidas en cajas y unidades.
class AccountMoveLine(models.Model):

        _inherit='account.move.line'

        quantity_unit = fields.Char(string="Unidades por empaque", compute = "_compute_quantity_unit")
        unidad  = fields.Integer(string="Cajas", default = 0)
        sub_unidad = fields.Integer(string="Unidades", default = 0)


        @api.onchange('unidad','sub_unidad')
        def onchange_unidad_sub_unidad(self):
                cantidad_anterior = self.quantity

                if self.unidad >= 0:
                        self.quantity = (self.unidad * self.product_id.quantity_uom) + self.sub_unidad
                if self.sub_unidad >= 0:
                        if self.product_id:
                                if self.sub_unidad >= self.product_id.quantity_uom:
                                        if self.product_id.quantity_uom == 0:
                                                raise ValidationError('El producto:' + str(self.product_id.name) + " en el campo cantidad por unidad de medida tiene valor de 0 debe agregar un valor valido")
                                        else:
                                                piezas_empaques = int(self.sub_unidad/self.product_id.quantity_uom)
                                        self.unidad = self.unidad + int(self.sub_unidad/self.product_id.quantity_uom)
                                        self.sub_unidad = self.sub_unidad - (piezas_empaques *  self.product_id.quantity_uom)

                        self.quantity = (self.unidad * self.product_id.quantity_uom) + self.sub_unidad
                if self.sub_unidad < 0 or self.unidad < 0:
                        raise ValidationError('No puedes agregar una cantidad negativa.')
        

        @api.depends('quantity_unit','product_id')
        def _compute_quantity_unit(self):
                for line in self:
                        if line.product_id:
                                line.quantity_unit = str(line.product_id.quantity_uom) + " " + str(line.product_id.uom_id.name)