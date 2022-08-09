# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    # Reemplazar 'state'
    # state = fields.Selection([
    #     ('draft', 'Quotation'),
    #     ('sent', 'Quotation Sent'),
    #     ('sale', 'Sales Order'),
    #     ('done', 'Locked'),
    #     ('cancel', 'Cancelled'),
    #     ('assigned_delivery', 'Asignado delivery'),
    #     ('delivered', 'Entregado delivery'),
    #     ('cancel_delivery', 'Cancelado delivery'),
    # ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    state = fields.Selection(selection_add=[
        ('assigned_delivery', 'Asignado delivery'),
        ('delivered', 'Entregado delivery'),
        ('cancel_delivery', 'Cancelado delivery'),
    ])
