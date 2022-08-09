# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InheritHrEmployee(models.Model):
    _inherit = 'hr.employee'

    delivery = fields.Boolean(string="Repartidor")
    state_delivery = fields.Selection([
        ('active_delivery', 'Activo para delivery'),
        ('inactive_delivery', 'Inactivo para delivery')
    ], string='Estado delivery')
