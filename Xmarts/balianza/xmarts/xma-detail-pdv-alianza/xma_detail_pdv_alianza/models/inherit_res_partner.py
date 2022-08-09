# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    is_pos = fields.Boolean(string="Es PDV")
