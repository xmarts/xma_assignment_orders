# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

#Modificación en pedidos de punto de venta para integración SIA-ODOO
class PosOrder(models.Model):

	_inherit='pos.order'

	company_id = fields.Many2one('res.company', string='Company')
	serie_id = fields.Many2one('ir.sequence', string="Serie", store=True)
	serie_related_ids = fields.Many2many('ir.sequence', compute="_compute_series_ptv")
	from_sia = fields.Boolean(string="Creado desde SIA?",store=True, readonly=True)

	@api.model
	def _complete_values_from_session(self, session, values):
		print ("Ingresa a _complete_values_from_session",values)
		if values.get('state') and values['state'] == 'paid':
			values['name'] = session.config_id.sequence_id._next()
		values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
		values.setdefault('fiscal_position_id', session.config_id.default_fiscal_position_id.id)
		values.setdefault('company_id', session.config_id.company_id.id)
		if not "amount_return" in values:
			values.setdefault('amount_return', 0)
		return values
	
	@api.onchange('payment_ids', 'lines')
	def _onchange_amount_all(self):
		for order in self:
			if order.pricelist_id:
				print ("Esto es order.pricelist_id",order.pricelist_id)
				currency = order.pricelist_id.currency_id
				print ("Esto es currency",currency)
				order.amount_paid = sum(payment.amount for payment in order.payment_ids)
				print ("Esto es order.amount_paid",order.amount_paid)
				order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.payment_ids)
				order.write({'amount_return':order.amount_return})
				print ("Esto es order.amount_return",order.amount_return)
				order.amount_tax = currency.round(sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines))
				amount_untaxed = currency.round(sum(line.price_subtotal for line in order.lines))
				order.amount_total = order.amount_tax + amount_untaxed
	
	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			if vals.get('serie_id'):
				obj_seq = self.env['ir.sequence'].browse(vals.get('serie_id'))
				if obj_seq:
					vals['name'] = obj_seq.next_by_id() or '/'

		pos_id = super(PosOrder, self).create(vals)
		return pos_id

	@api.depends('serie_related_ids')
	def _compute_series_ptv(self):
		for ptv in self:
			serie_related = self.env['ir.sequence'].search([('company_id','=',ptv.company_id.id),('ptv_related_id','=',ptv.session_id.config_id.id)])
			serie_list = []
			for serie in serie_related:
				serie_list.append(serie.id)
			ptv.serie_related_ids = [(6,0, serie_list)]
			
class PosSession(models.Model):

	_inherit='pos.session'

	from_sia = fields.Boolean(string="Creado desde SIA?", store=True, readonly=True)