# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PostFestiveDays(models.Model):
    _name = 'post.festive.days'
    _description = 'post.festive.days'

    config_id = fields.Many2one(
        comodel_name='pos.config',
        string="Sucursal")
    description = fields.Char(string="Descripción")
    date_start = fields.Datetime(string="Fecha inicio")
    date_end = fields.Datetime(string="Fecha fin ")

    def _set_pdv_availability_cron(self):
        current_date_time = fields.Datetime.now()
        pfd = self.env['post.festive.days'].search([
            ('date_start', '<=', current_date_time),
            ('date_end', '>=', current_date_time)])
        for item in pfd:
            item.config_id.pos_availability = 'ss'
        pfd = self.env['post.festive.days'].search([
            ('date_end', '<', current_date_time),
            ('config_id.pos_availability', '=', 'ss')])
        for item in pfd:
            item.config_id.pos_availability = 'es'
