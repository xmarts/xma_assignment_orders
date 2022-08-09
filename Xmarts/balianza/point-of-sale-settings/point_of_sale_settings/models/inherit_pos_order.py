# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InheritPosOrder(models.Model):
    _inherit = 'pos.order'

    repart = fields.Many2one(
        'res.partner',
        string="Repartidor"
    )

    @api.model
    def get_series_pos_order(self, configId=0):
        try:
            print("pppppppppppppppppppppppppppppppppppppppppppppp configId:", configId)
            if configId:
                sequence = self.env['ir.sequence'].search([
                    ('ptv_related_id','=', int(configId))])
                if sequence:
                    lista = []
                    for seq in sequence:
                        print("000000000000000000000000 seq.serie.lower().find('my'):", seq.serie.lower().find('my'), ", seq.serie.lower():", seq.serie.lower())
                        if seq.serie.lower().find('my') > 0:
                            print("111111111111111111111111")
                            lista.append({'indice': 0, 'id': seq.id, 'data': seq.serie})
                        elif seq.serie.lower().find('mn') > 0:
                            print("222222222222222222222222")
                            lista.append({'indice': 1, 'id': seq.id, 'data': seq.serie})
                        print("forrrrrrrrrrrrrrrrrrrrrrrrrrrrrr ", lista)
                    return lista
                else:
                    return []
            else:
                return {'error': ''}
        except Exception as e:
            return {'error': str(e)}

    @api.model
    def _order_fields(self, ui_order):
        print("ui_orderrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr ", ui_order)
        order_fields = super(InheritPosOrder, self)._order_fields(ui_order)
        order_fields['serie_id'] = ui_order.get('serie_id', False)
        order_fields['repart'] = ui_order.get('repart', False)
        return order_fields

    @api.model
    def create_from_ui(self, orders, draft=False):
        for order in orders:
            print("7777777777777777777777777777777777777777777777777777777777777777: ", orders)
            for lines in order['data']['lines']:
                for line in lines:
                    print("9999999999999999999999999999999999999999999999999999999999999999999999 1: ", line)
                    if line != 0:
                        print("9999999999999999999999999999999999999999999999999999999999999999999999 2: ", line)
                        if line.get('qty', ''):
                            print("9999999999999999999999999999999999999999999999999999999999999999999999 3: ", line)
                            if int(line.get('qty_caja', 0)) >= 1:
                                print("9999999999999999999999999999999999999999999999999999999999999999999999 4: ", line)
                                qty = int(line.get('qty', 0))
                                qty_caja = int(line.get('qty_caja', 0))
                                qty_product_x_caja = int(line.get('qty_product_x_caja', 0))
                                line['qty'] = qty + (qty_caja * qty_product_x_caja)
        return super(InheritPosOrder, self).create_from_ui(orders, draft)
