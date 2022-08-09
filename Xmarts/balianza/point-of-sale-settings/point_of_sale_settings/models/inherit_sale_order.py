# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    tipo_compra = fields.Selection([
        ('compra_mayoreo', 'Compra por Mayoreo'),
        ('compra_minoreo', 'Compra por Minoreo')
    ],string="Tipo de Compra", compute="tipo_de_compra")

    def tipo_de_compra(self):
        for rec in self:
            if rec.serie_id:
                if rec.serie_id.serie.lower().find('my') > 0:
                    print("111111111111111111111111")
                    rec.tipo_compra = 'compra_mayoreo'
                elif rec.serie_id.serie.lower().find('mn') > 0:
                    print("222222222222222222222222")
                    rec.tipo_compra = 'compra_minoreo'
            else:
                rec.tipo_compra = ''