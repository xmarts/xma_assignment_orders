from odoo import fields, models, _
from datetime import date
import base64

class AccountMove(models.Model):
    _inherit = "account.move"


    

    def action_invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))

        self.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None):
        if self.model == 'account.move' and res_ids:
            invoice_reports = (self.env.ref('account.account_invoices_without_payment'), self.env.ref('account.account_invoices'))
            if self in invoice_reports:
                moves = self.env['account.move'].browse(res_ids)
                if any(not move.is_invoice(include_receipts=True) for move in moves):
                    raise UserError(_("Only invoices could be printed."))