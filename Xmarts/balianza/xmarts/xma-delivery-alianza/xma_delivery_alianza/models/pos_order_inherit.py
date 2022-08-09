from odoo import fields, models, _, api
from datetime import date
import base64
from . import amount_to_text

class PosOrder(models.Model):
    _inherit = 'pos.order'

    amount_total_text = fields.Char(
        compute='_get_amount_to_text', 
        string='Monto en Texto', 
        readonly=True, 
        help='Monto de los pedidos en Letra'
    )

    @api.depends('amount_total')
    def _get_amount_to_text(self):
        self.amount_total_text = amount_to_text.\
            get_amount_to_text(self, self.amount_total, self.currency_id.name)
    
    signature = fields.Binary(
        string="Firma"
    )

    date_today = fields.Date(

    )
    
    survey_send = fields.Boolean(
        string="Encuesta enviada",
        default=False
    )

    send_ticket = fields.Boolean(
        string="Ticket enviado",
        default=False
    )

    invoice_send = fields.Boolean(
        string="Factura Enviada",
        default=False
    )

    order_cancellatios_id = fields.Many2many(
        'pos.order.cancellations',
        string="Motivo de cancelacion"
    )

    description = fields.Char(
        string="Descripcion"
    )

    repartidor = fields.Many2one(
        'hr.employee',
        string="Repartidor"
    )
    

    def get_discount_order(self):
        discount = 0
        for rec in self.lines:
            disc  = (rec.discount * rec.price_unit) / 100
            discount += disc
        return discount

    def create(self, vals):
        vals['date_today'] = date.today()
        return super(PosOrder, self).create(vals)

    def send_ticket_order_individual(self):
        for order in self:
            view = 'xma_delivery_alianza.action_report_pos_order_alianza'
            client = {
                'email': order.partner_id.email,
                'name': order.partner_id.name
            }
            name = order.pos_reference
            mess = "<p>Hola %s,<br/>Te hacemos entrega del ticket de tu compra: %s. </p>"
            message = _(mess) % (client['name'], name)
            report = self.env.ref(view)._render_qweb_pdf(order.ids[0])
            filename = name + '.pdf'
            # filename = 'Receipt-' + name + '.jpg'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]), 
                'res_model': 'pos.order',
                'res_id': order.ids[0],
                'mimetype': 'application/x-pdf',
                # 'mimetype': 'image/jpeg',
            })

            mail_values = {
                'subject': _('Receipt %s', name),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': client['email'],
                'attachment_ids': [(4, attachment.id)],
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        self.send_ticket = True

    def cron_send_ticket_orders(self):
        view = 'xma_delivery_alianza.action_report_pos_order_alianza'
        print(view)
        # view = 'point_of_sale.sale_details_report'
        pos_order = self.env['pos.order']
        orders =  pos_order.search([
            ('date_today','=', date.today()),
            ('send_ticket', '=', False)
        ])
        for order in orders:
            client = {
                'email': order.partner_id.email,
                'name': order.partner_id.name
            }
            name = order.pos_reference
            message = _("<p>Hola %s,<br/>Te hacemos entrega del ticket de tu compra:  %s. </p>") % (client['name'], name)
            report = self.env.ref(view)._render_qweb_pdf(order.ids[0])
            #filename = name + '.pdf'
            filename = 'Receipt-' + name + '.jpg'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]), 
                'res_model': 'pos.order',
                'res_id': order.ids[0],
                #'mimetype': 'application/x-pdf',
                'mimetype': 'image/jpeg',
            })

            mail_values = {
                'subject': _('Receipt %s', name),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': client['email'],
                'attachment_ids': [(4, attachment.id)],
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            order.send_ticket = True


    def cron_send_invoice(self):
        view = 'xma_delivery_alianza.action_report_account_move_alianza'
        print(view)
        # view = 'point_of_sale.sale_details_report'
        pos_order = self.env['pos.order']
        orders =  pos_order.search([
            ('date_today','=', date.today()),
            ('send_ticket', '=', False),
        ])
        for order in orders:
            client = {
                'email': order.partner_id.email,
                'name': order.partner_id.name
            }
            name = order.pos_reference
            message = _("<p>Hola %s,<br/>Hacemos entrega de tu factura de %s. </p>") % (client['name'], name)
            report = self.env.ref(view)._render_qweb_pdf(order.ids[0])
            filename = name + '.pdf'
            # filename = 'Receipt-' + name + '.jpg'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]), 
                'res_model': 'pos.order',
                'res_id': order.account_move.ids[0],
                'mimetype': 'application/x-pdf',
                # 'mimetype': 'image/jpeg',
            })

            mail_values = {
                'subject': _('Receipt %s', name),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': client['email'],
                'attachment_ids': [(4, attachment.id)],
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            order.invoice_send = True
    
    def send_invoice_order_individual(self):
        view = 'xma_delivery_alianza.action_report_account_move_alianza'
        for order in self:
            client = {
                'email': order.partner_id.email,
                'name': order.partner_id.name
            }
            name = order.pos_reference
            message = _("<p>Hola %s,<br/>Hacemos entrega de tu factura/ de  %s. </p>") % (client['name'], name)
            report = self.env.ref(view)._render_qweb_pdf(order.ids[0])
            filename = name + '.pdf'
            # filename = 'Receipt-' + name + '.jpg'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]), 
                'res_model': 'pos.order',
                'res_id': order.account_move.ids[0],
                'mimetype': 'application/x-pdf',
                # 'mimetype': 'image/jpeg',
            })

            mail_values = {
                'subject': _('Receipt %s', name),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': client['email'],
                'attachment_ids': [(4, attachment.id)],
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        self.invoice_send = True
