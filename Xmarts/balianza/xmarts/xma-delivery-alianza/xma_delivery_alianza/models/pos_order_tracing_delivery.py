from attr import field
from odoo import fields, models


class PosOrderTracingDelivery(models.Model):
    _name = 'pos.order.tracing.delivery'
    _description='Localization Delivery'
    _order='id desc'

    name = fields.Char(
        string='Folio'
    )

    delivery_id = fields.Many2one(
        'hr.employee',
        string='Repartidor'
    )

    order_id = fields.Many2one(
        'pos.order',
        string='Pedido'
    )

    latitude = fields.Float(
        string='Latitud',
        digits=(3,6)
    )

    longitude = fields.Float(
        string='Longitud',
        digits=(3,6)
    )

    def view_delivery_in_map(self):
        for rec in self:
            rec.delivery_id.partner_id_delivery.\
                partner_latitude = rec.latitude
            rec.delivery_id.partner_id_delivery.\
                partner_longitude = rec.longitude

            action = {
                "type": "ir.actions.act_window",
                "view_mode": "map",
                "res_model": "res.partner",
                "target": "fullscreen",
                "domain":[
                    ('id','=',rec.delivery_id.partner_id_delivery.id)
                ]
            }
            print('mapa')
            return action
