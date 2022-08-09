from odoo import fields, models
from datetime import date, datetime, timedelta


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    url_survey = fields.Char(
        string="URL de Encuesta"
    )
    template_id_survey = fields.Many2one(
        'mail.template',
        string="Plantilla de correo"
    )

    def cron_send_surveys_execute(self):
        today = date.today()
        datetime_now = datetime.now()
        ctx = dict(self._context)
        view = 'xma_delivery_alianza.mail_template_user_surveys_alianza'
        tmpl_id = self.env.ref(view).id
        survey_inv = self.env['survey.survey']
        pos_order = self.env['pos.order']
        ordenes = pos_order.search([
            ('date_today','=', today ),
            ('is_invoiced', '=', True)
        ])
        
        print(ordenes)
        surv = survey_inv.\
            search([
                ('template_id_survey','=',tmpl_id)
            ], limit=1)
        url = surv.url_survey
        for partners in ordenes:
            ctx = {}
            ctx['email_to'] = partners.partner_id.email
            ctx['url'] = url
            ctx['send_email'] = True
            date_dear = datetime_now + timedelta(days=7)
            ctx.update({
                'url':url,
                'partner_name':partners.partner_id.name,
                'date_dear':date_dear.strftime('%d/%m/%y')
            })
            email_values = {'email_to': partners.partner_id.email or ''}
            template = self.env.ref(view)
            template.with_context(ctx).\
                send_mail(
                    partners.partner_id.id,
                    email_values=email_values,
                    raise_exception=False
                )
            partners.survey_send = True
