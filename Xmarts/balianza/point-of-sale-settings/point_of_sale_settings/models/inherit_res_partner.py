# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InheritResPartner(models.Model):
    _inherit = "res.partner"

    customer_created_by = fields.Selection([
        ('cliente_creado_pdv','PDV'),
        ('cliente_creado_model_venta','Ventas')
    ], string="Cliente creado desde",
    readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(InheritResPartner, self).create(vals_list)
        partners.create_msj_log()
        return partners

    def create_msj_log(self):
        msj = ''
        if self.customer_created_by == 'cliente_creado_pdv':
            msj = 'Cliente creado por PDV'
        elif self.customer_created_by == 'cliente_creado_model_venta':
            msj = 'Cliente creado por Ventas'
        if msj != '':
            odoobot = self.env.ref('base.partner_root')
            sms = self.env['mail.message'].create({
                'model': self._name,
                'res_id': self.id,
                'body': msj,
                'message_type': 'notification',
                'subtype_id': 2,
                'author_id': odoobot.id,
            })
            self.env['mail.notification'].create({
                'mail_message_id': sms.id,
                'res_partner_id': odoobot.id,
                'notification_type': 'sms',
                'notification_status': 'exception',
                'failure_type': 'sms_credit',
            })

    @api.model
    def create_from_ui(self, partner):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        if partner.get('image_1920'):
            partner['image_1920'] = partner['image_1920'].split(',')[1]
        partner_id = partner.pop('id', False)
        print("tttttttttttttttttttttttttttttttttttttttttttttt ", partner_id)
        if partner_id:  # Modifying existing partner
            if partner.get('vat'):
                commercial_partner_id = self.browse(partner_id).commercial_partner_id.id
                valid_rfc = self.search_count([('vat','=ilike', str(partner['vat'])), ('commercial_partner_id','!=', commercial_partner_id)])
                if valid_rfc == 0:
                    self.browse(partner_id).write(partner)
                else:
                    msj = 'ExisteRFC'
                    return msj
            else:
                self.browse(partner_id).write(partner)
        else:
            if partner.get('vat'):
                print("RFC::::::::::::::::::::::::::::::::::::::::::::.. ", partner.get('vat'))
                valid_rfc = self.search_count([('vat','=', str(partner['vat']))])
                print("RFCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC ", valid_rfc)
                if valid_rfc == 0:
                    partner_id = self.create(partner).id
                else:
                    msj = 'ExisteRFC'
                    return msj
            else:
                partner_id = self.create(partner).id
        return partner_id
