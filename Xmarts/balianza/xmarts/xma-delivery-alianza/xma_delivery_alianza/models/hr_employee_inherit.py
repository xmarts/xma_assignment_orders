from odoo import fields, models
from random import choice
import uuid


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    code_delivery = fields.Char(
        string="Código delivery"
    )

    user_login = fields.Char(
        string="Usuario"
    )

    partner_id_delivery = fields.Many2one(
        'res.partner',
        string='Usuario del repartidor'
    )

    password_login = fields.Char(
        string="Contraseña"
    )

    tacking_delivery_ids = fields.One2many(
        'pos.order.tracing.delivery',
        'delivery_id'
    )

    token = fields.Char('Security Token', 
        copy=False, 
        default=lambda self: str(uuid.uuid4()),
        required=True
    )

    def _login_app(self, data):
        if data:
            user = self.search([
                ('user_login', '=', data['user_login']),
                ('password_login', '=', data['password_login']),
                ('code_delivery', '=', data['code_delivery'])]
            )
            if(user): return {'data': {'ok': True, 'token': user.token}}
        return False

    def  execute_ramdom_key(self):
        model = self.env['hr.employee'].search([('delivery', '=', True)])
        for rec in model:
            rec.get_ramdom_key()

    def get_ramdom_key(self):
        for rec in self:
            longitud = 6
            numeros = "0123456789"
            minusculas = "abcdefghijklmnopqrstuvwxyz"
            mayusculas = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            key_ramdom= ""
            key_ramdom = key_ramdom.join(
                [choice(numeros+minusculas+mayusculas)
                    for i in range(longitud)]
            )
            rec.code_delivery = key_ramdom
    
    def del_ramdom_key(self):
        model = self.env['hr.employee'].search([('delivery', '=',True )])
        for rec in model:
            rec.code_delivery = ''
