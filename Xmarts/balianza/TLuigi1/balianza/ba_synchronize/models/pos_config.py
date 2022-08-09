# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError


# Añadido para complementar integración SIA-ODOO en puntos de venta.
class PosConfig(models.Model):
    _inherit = 'pos.config'

    code = fields.Char(string="Codigo punto de venta")
    liga = fields.Char(string="Liga")
    status = fields.Boolean(string="Estatus")
    database = fields.Char(string="Base")

    def name_get(self):
        result = []
        for config in self:
            result.append((config.id, "%s (%s)" % (config.code, config.name)))
        return result

    # pendiente
    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_invoice_journal(self):
        if self.invoice_journal_id and self.invoice_journal_id.company_id.id != self.company_id.id:
            print("Pasa en _check_company_invoice_journal")


class PosAsignation(models.TransientModel):
    _inherit = 'res.config.settings'

    pdv_client_radio = fields.Float(string='Radio de cliente PDV (Km)', store=True)
    pdv_delivery_radio = fields.Float(string='Radio de repartidor PDV (km)', store=True)

    def set_values(self):
        super(PosAsignation, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('pos_config.pdv_client_radio', float(self.pdv_client_radio))
        set_param('pos_config.pdv_delivery_radio', float(self.pdv_delivery_radio))

    @api.model
    def get_values(self):
        res = super(PosAsignation, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res['pdv_client_radio'] = float(get_param('pos_config.pdv_client_radio'))
        res['pdv_delivery_radio'] = float(get_param('pos_config.pdv_delivery_radio'))
        return res

