from odoo import fields,models


class SurveyInvite(models.TransientModel):
    _inherit="survey.invite"

    survey_start_url_rel = fields.Char(
        string="URL",
        related="survey_start_url",
        store=True)

    def action_invite(self):
        self.survey_id.url_survey = self.survey_start_url_rel
        return super(SurveyInvite, self).action_invite()