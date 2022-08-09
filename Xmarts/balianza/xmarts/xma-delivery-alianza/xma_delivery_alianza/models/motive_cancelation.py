from odoo import fields, models

class MotiveCancelation(models.Model):
    _name = 'pos.order.cancellations'

    name = fields.Char(
        string="Motivo de Cancelacion"

    )

    visible = fields.Boolean(
        string="visible"
    )

    color = fields.Integer(
        string="Color Index"
    )
