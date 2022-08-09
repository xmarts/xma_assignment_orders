# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InheritPosConfig(models.Model):
    _inherit = 'pos.config'

    contact_id = fields.Many2one(
        comodel_name='res.partner',
        string="Ubicación",
        domain="[('is_pos', '=', True)]")
    contact_address_complete = fields.Char(
        string="Dirección de contacto completa",
        related="contact_id.contact_address_complete")
    is_delivery = fields.Boolean(string="Delivery")
    resource_calendar_is = fields.Many2one(
        comodel_name='resource.calendar',
        string="Horas de servicio")
    pos_availability = fields.Selection([
        ('ss', 'Sin servicio'),
        ('es', 'En servicio')
    ],
        string='Disponibilidad del PDV',
        default='ss')
