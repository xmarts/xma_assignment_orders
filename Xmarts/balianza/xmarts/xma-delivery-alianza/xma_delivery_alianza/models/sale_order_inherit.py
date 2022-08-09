from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_cancellatios_id = fields.Many2many(
        'pos.order.cancellations',
        string="Motivo de cancelacion"
    )

    description = fields.Char(
        string="Descripcion"
    )