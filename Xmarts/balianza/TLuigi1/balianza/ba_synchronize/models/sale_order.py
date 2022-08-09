# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _, modules
from datetime import datetime, timedelta
from odoo.http import request
from functools import partial
from itertools import groupby
from collections import defaultdict
import logging
import base64
#import js2py
#import execjs
from odoo.tools.misc import format_date
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools.float_utils import float_repr
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round, float_is_zero
import json

#Modificaciones para tener control de gastos relacionados, calculo de impuestos, control en cajas y unidades, gestión de almacenes y restricción en productos en stock para selección en pedido.
class SaleOrder(models.Model):

	_inherit='sale.order'

	taxes_by_group = fields.One2many('sale.line.tax', 'sale_related', store=True)
	serie_id = fields.Many2one('ir.sequence', string="Serie", store=True)
	stock_save = fields.Boolean( string="Serie", store=True,default=False)

	def update_stock(self):
		#print ("Ingresa a updated_stock")
		self.order_line._action_launch_stock_rule()
	
	def save_order(self):
		#print ("Se guardo registro")
		if self.state in ('draft','sent'):
			for order in self:
				unico_impuesto = {}
				for line in order.order_line:
					if line.taxes_by_group:
						impuestos = json.loads(line.taxes_by_group)
						for (key, val) in impuestos.items():
							#print("Esto es key",key)
							#print("esto es val",val)
							if key in unico_impuesto:
								for (key1, val1) in unico_impuesto.items():
									#print("Esto es key1",key1)
									#print("esto es val1",val1)
									if key == key1:
										unico_impuesto.update({
											str(key):{
												'nombre':val1['nombre'],
												'base':val1['base'] + val['base'],
												'monto':val1['monto'] + val['monto'],
												}
											})
							else:
								unico_impuesto.update({
									str(key):{
										'nombre':val['impuesto'],
										'base':val['base'],
										'monto':val['monto'],
										}
									})
				if not order.order_line and order.taxes_by_group:
					registros = self.env['sale.line.tax'].search([('sale_related', '=', self._origin.id)])
					registros.unlink()
				if order.order_line:
					registros = self.env['sale.line.tax'].search([('sale_related', '=', self._origin.id)])
					if registros:
						registros.unlink()
					for (key1, val1) in unico_impuesto.items():
						#print("Pasa aqui al final",key1)
						#print("Pasa aqui al final val1",val1)
						values = {
							'name':val1['nombre'],
							'monto_base':round(val1['base'],4),
							'total_impuesto':round(val1['monto'], 4) ,
							'sale_related':self._origin.id,
						} 
						self.env['sale.line.tax'].create(values)


			#print ("Esto es unico_impuesto",unico_impuesto)

			for line in self.order_line:
				#print ("Esto es line.product_id.product_tmpl_id",line.product_id.product_tmpl_id)
				line.product_id.product_tmpl_id.calculate_reserved_quantity_ba()
				#print("Esta recorriendo line",line)
				if line.product_uom_qty == 0 and line.unidad == 0 and line.sub_unidad == 0:
					raise UserError(_('El producto ' + str(line.product_id.name) + ' no tiene cantidad agregada.'))
				reservas = self.env['reserved.product'].search([('order_id','=',self.id),('product_id','=',line.product_id.product_tmpl_id.id)])
				if reservas:
					for reserva in reservas:
						line.product_id.cantidades_reservadas = line.product_id.cantidades_reservadas - reserva.cantidad + line.product_uom_qty
						reserva.write({'cantidad': line.product_uom_qty})
				else:
					if line.product_uom_qty != 0:
						line.product_id.cantidades_reservadas = line.product_id.cantidades_reservadas + line.product_uom_qty
						self.env['reserved.product'].create({'order_id': self.id , 'product_id': line.product_id.product_tmpl_id.id , 'cantidad': line.product_uom_qty})
		else:
			return


	def write(self, values):
		#print ("Esto es self.stock_save en write",self.stock_save)
		if self.stock_save == True:
			result = super(SaleOrder, self).write(values)
			self.update_stock()
			self.save_order()
			return result
		#print("Esto es values",values)
		values['stock_save'] = True
		#print("Esto es values abajo",values)
		result = super(SaleOrder, self).write(values)
		self.save_order()
		
		#if self.state != 'sale':
		#	self.action_confirm()
		#if self.state != 'sale':
		#	self.order_line._action_launch_stock_rule()
		return result

	

	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			if vals.get('serie_id'):
				obj_seq = self.env['ir.sequence'].browse(vals.get('serie_id'))
				if obj_seq:
					vals['name'] = obj_seq.next_by_id() or '/'
					
		so_id = super(SaleOrder, self).create(vals)
		so_id.save_order()
		#print ("Esto es self.state en create",so_id.state)
		#if so_id.state != 'sale':
		#	so_id.action_confirm()
		#if so_id.state != 'sale':
		#	print ("Ingresa a so_id.state != sale",so_id.order_line)
		#	so_id.order_line._action_launch_stock_rule()
		return so_id

	def _action_confirm(self):
		self.order_line._action_launch_stock_rule()
		for line in self.order_line:
			if line.product_uom_qty == 0:
				raise ValidationError("El producto: " + str(line.product_id.name) + " no tiene cantidad agregada, actualice las partidas para reservar el producto primero modificando las cajas y unidades requeridas.")
			reserva =  self.env['reserved.product'].search([('order_id','=',line.order_id.id),('product_id','=',line.product_id.product_tmpl_id.id)])
			if reserva:
				reserva.unlink()
			line.product_id.cantidades_reservadas = line.product_id.cantidades_reservadas - line.product_uom_qty
		return super(SaleOrder, self)._action_confirm()

	def action_cancel(self):
		documents = None
		for sale_order in self:
			for line in sale_order.order_line:
				if sale_order.state in ('draft','sent'):
					line.product_id.cantidades_reservadas = line.product_id.cantidades_reservadas - line.product_uom_qty
					reserva =  self.env['reserved.product'].search([('order_id','=',line.order_id.id),('product_id','=',line.product_id.product_tmpl_id.id)])
					if reserva:
						reserva.unlink()
				line.product_id.product_tmpl_id.calculate_reserved_quantity_ba()
				line.product_uom_qty = 0
				
			if sale_order.state == 'sale' and sale_order.order_line:
				sale_order_lines_quantities = {order_line: (order_line.product_uom_qty, 0) for order_line in sale_order.order_line}
				documents = self.env['stock.picking']._log_activity_get_documents(sale_order_lines_quantities, 'move_ids', 'UP')
		self.picking_ids.filtered(lambda p: p.state != 'done').action_cancel()
		if documents:
			filtered_documents = {}
			for (parent, responsible), rendering_context in documents.items():
				if parent._name == 'stock.picking':
					if parent.state == 'cancel':
						continue
				filtered_documents[(parent, responsible)] = rendering_context
			self._log_decrease_ordered_quantity(filtered_documents, cancel=True)
		return super(SaleOrder, self).action_cancel()

	def unlink(self):
		for order in self:
			if order.state not in ('draft', 'cancel'):
				raise UserError(_('You can not delete a sent quotation or a confirmed sales order. You must first cancel it.'))
		for line in self.order_line:
			line.unlink()
		return super(SaleOrder, self).unlink()
	
	@api.onchange('order_line')
	def onchange_order_line(self):
		product = []
		for order in self.order_line:
			#print ("Entra al onchange order_line",order.product_id)
			if order.product_id in product:
				raise ValidationError("El producto: " + str(order.product_id.name) + " ya se encuentra agregado al pedido.")
			else:
				product.append(order.product_id)
				
	def _create_invoices(self, grouped=False, final=False, date=None):
		if not self.env['account.move'].check_access_rights('create', False):
			try:
				self.check_access_rights('write')
				self.check_access_rule('write')
			except AccessError:
				return self.env['account.move']

		invoice_vals_list = []
		invoice_item_sequence = 0 
		for order in self:
			order = order.with_company(order.company_id)
			current_section_vals = None
			down_payments = order.env['sale.order.line']

			invoice_vals = order._prepare_invoice()
			invoiceable_lines = order._get_invoiceable_lines(final)

			if not any(not line.display_type for line in invoiceable_lines):
				raise self._nothing_to_invoice_error()

			invoice_line_vals = []
			down_payment_section_added = False
			sequence_invoice = 1
			for line in invoiceable_lines:
				if not down_payment_section_added and line.is_downpayment:
					invoice_line_vals.append(
						(0, 0, order._prepare_down_payment_section_line(
						sequence=invoice_item_sequence, 
						)),
						)
					dp_section = True
					invoice_item_sequence += 1
				moves = self.env['stock.picking'].search([('sale_id','=',line.order_id.id),('state','in',('confirmed','assinged','done'))], order="id asc", limit=1)
				#print ("Esto es moves",moves)
				for move in moves:
					for line_move in move.move_line_ids_without_package:
						if line_move.product_id == line.product_id:
							#print ("Esto es el context actual",self.env.context)
							context = self.env.context.copy()
							context.update({'sequence_invoice': sequence_invoice})
							#context.update({'pedimento': line_move.pedimento})
							context.update({'product_qty': line_move.qty_done})
							self.env.context = context

							#print("Esto es el context modificado",self.env.context)
							invoice_line_vals.append(
								(0, 0, line._prepare_invoice_line(
									sequence=invoice_item_sequence,
									)),
								)
							invoice_item_sequence += 1
							sequence_invoice += 1
			invoice_vals['invoice_line_ids'] += invoice_line_vals
			invoice_vals_list.append(invoice_vals)

		if not invoice_vals_list:
		    raise self._nothing_to_invoice_error()

		if not grouped:
		    new_invoice_vals_list = []
		    invoice_grouping_keys = self._get_invoice_grouping_keys()
		    for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
		        origins = set()
		        payment_refs = set()
		        refs = set()
		        ref_invoice_vals = None
		        for invoice_vals in invoices:
		            if not ref_invoice_vals:
		                ref_invoice_vals = invoice_vals
		            else:
		                ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
		            origins.add(invoice_vals['invoice_origin'])
		            payment_refs.add(invoice_vals['payment_reference'])
		            refs.add(invoice_vals['ref'])
		        ref_invoice_vals.update({
		            'ref': ', '.join(refs)[:2000],
		            'invoice_origin': ', '.join(origins),
		            'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
		        })
		        new_invoice_vals_list.append(ref_invoice_vals)
		    invoice_vals_list = new_invoice_vals_list

		if len(invoice_vals_list) < len(self):
		    SaleOrderLine = self.env['sale.order.line']
		    for invoice in invoice_vals_list:
		        sequence = 1
		        for line in invoice['invoice_line_ids']:
		            line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
		            sequence += 1

		moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

		if final:
		    moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
		for move in moves:
		    move.message_post_with_view('mail.message_origin_link',
		        values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
		        subtype_id=self.env.ref('mail.mt_note').id
		    )
		return moves

	@api.depends('order_line.price_total')
	def _amount_all(self):
		#print("Esto es _amount_all",self.env.context)
		for order in self:
			amount_untaxed = amount_tax = 0.0
			for line in order.order_line:
				amount_untaxed += line.price_subtotal
				amount_tax += line.price_tax

			order.update({
				'amount_untaxed': amount_untaxed,
				'amount_tax': amount_tax,
				'amount_total': amount_untaxed + amount_tax,
				})

	

class SaleOrderLine(models.Model):

	_inherit='sale.order.line'

	product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=0, copy=False)
	price_subtotal_base = fields.Float(string="Subtotal base para IVA",compute="_compute_amount", store=True)
	taxes_by_group = fields.Char("Grupo de impuestos", compute="_compute_sale_taxes_by_line", store=True)
	quantity_unit = fields.Char(string="Unidades por empaque", compute="_compute_quantity_unit", store=True)
	unidad  = fields.Integer(string="Cajas", default = 0)
	sub_unidad = fields.Integer(string="Unidades", default = 0)
	cantidad = fields.Float(string="Cantidad", related='product_uom_qty')
	unidades_sin_reserva = fields.Float(string="Disponible unidades (no reservado)",compute='_compute_qty_at_date')
	disponible_para_pedido = fields.Float(string="Disponible para pedido",compute='_compute_qty_at_date')
	grados_alcohol = fields.Float(string="Grados alcohol", default = 0)
	contenido = fields.Integer(string="Contenido", default = 0)
	pricelist_id = fields.Many2one('product.pricelist',string="L.P.")
	pricelist_name = fields.Char(related='pricelist_id.code',string="L.P.")
	box_price = fields.Float(string="Precio caja")
	inv_available = fields.Text(String="Inv.Disponible",compute='_compute_qty_at_date')

	@api.model
	def create(self, vals):
		so_line_id = super(SaleOrderLine, self).create(vals)
		if so_line_id.state != 'sale':
			#rint ("Ingresa a so_line_id.state != sale",so_line_id)
			so_line_id._action_launch_stock_rule()
		return so_line_id


	@api.onchange('product_uom_qty')
	def _onchange_product_uom_qty(self):
		if self._origin:
			product_uom_qty_origin = self._origin.read(["product_uom_qty"])[0]["product_uom_qty"]
		else:
			product_uom_qty_origin = 0

		if self.state == 'sale' and self.product_id.type in ['product', 'consu'] and self.product_uom_qty < product_uom_qty_origin:
			# Do not display this warning if the new quantity is below the delivered
			# one; the `write` will raise an `UserError` anyway.
			if self.product_uom_qty < self.qty_delivered:
				return {}

			warning_mess = {
				'title': _('Ordered quantity decreased!'),
				'message' : _('You are decreasing the ordered quantity! Do not forget to manually update the delivery order if needed.'),
			}
			return {'warning': warning_mess}
		return {}


	def _action_launch_stock_rule(self, previous_product_uom_qty=False):
		#print ("Pasa en _action_launch_stock_rule ++++++++------",self)
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		procurements = []
		for line in self:
			#print ("Esto es line.state dentro de _action_launch_stock_rule",line.state)
			#print ("Esto es line.product_uom_qty dentro de _action_launch_stock_rule",line.product_uom_qty)
			line = line.with_company(line.company_id)
			#Linea base comentada y remplazada
			#if line.state != 'sale' or not line.product_id.type in ('consu','product'):
			if line.state not in ('sale','draft') or not line.product_id.type in ('consu','product'):
				continue

			qty = line._get_qty_procurement(previous_product_uom_qty)
			#print ("Esto es qty arriba",qty)
			#Funcionalidad base comentada para permitir actualizar siempre las cantidades reservadas en movimiento de salida
			#if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
			#	continue

			group_id = line._get_procurement_group()
			#print ("Esto es group_id",group_id)
			if not group_id:
				group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
				line.order_id.procurement_group_id = group_id
			else:
				# In case the procurement group is already created and the order was
				# cancelled, we need to update certain values of the group.
				#print ("Ingresa a Else")
				updated_vals = {}
				if group_id.partner_id != line.order_id.partner_shipping_id:
					updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
				if group_id.move_type != line.order_id.picking_policy:
					updated_vals.update({'move_type': line.order_id.picking_policy})
				if updated_vals:
					group_id.write(updated_vals)

			values = line._prepare_procurement_values(group_id=group_id)
			#print ("Llegó a values",values)
			#print ("Llegó a line.product_uom_qty",line.product_uom_qty)
			#print ("Llegó a qty",qty)
			product_qty = line.product_uom_qty - qty
			line_uom = line.product_uom
			quant_uom = line.product_id.uom_id
			product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
			procurements.append(self.env['procurement.group'].Procurement(
				line.product_id, product_qty, procurement_uom,
				line.order_id.partner_shipping_id.property_stock_customer,
				line.name, line.order_id.name, line.order_id.company_id, values))
		#print ("Esto es procurements",procurements)
		if procurements:
			self.env['procurement.group'].run(procurements)
		return True


	@api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
	def _compute_qty_delivered(self):
		#print ("Ingresa a _compute_qty_delivered")
		super(SaleOrderLine, self)._compute_qty_delivered()

		for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
			if line.qty_delivered_method == 'stock_move':
				qty = 0.0
				outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
				for move in outgoing_moves:
					if move.state != 'done':
						continue
					qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
				for move in incoming_moves:
					if move.state != 'done':
						continue
					qty -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
				line.qty_delivered = qty
				line.product_id.product_tmpl_id.calculate_reserved_quantity_ba()
				#print("Esto es line.qty_delivered",qty)


	@api.depends(
		'product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.commitment_date',
		'move_ids', 'move_ids.forecast_expected_date', 'move_ids.forecast_availability')
	def _compute_qty_at_date(self):
		#print ("Ingresa a _compute_qty_at_date ++++++++++++++++++++",self)
		treated = self.browse()
		for line in self.filtered(lambda l: l.state == 'sale'):
			#print ("Ingresa en 1")
			if not line.display_qty_widget:
				continue
			moves = line.move_ids.filtered(lambda m: m.product_id == line.product_id)
			line.forecast_expected_date = max(moves.filtered("forecast_expected_date").mapped("forecast_expected_date"), default=False)
			line.qty_available_today = 0
			line.free_qty_today = 0
			line.unidades_sin_reserva = 0
			line.disponible_para_pedido = 0
			line.inv_available = ""
			for move in moves:
				line.qty_available_today += move.product_uom._compute_quantity(move.reserved_availability, line.product_uom)
				line.free_qty_today += move.product_id.uom_id._compute_quantity(move.forecast_availability, line.product_uom)
				#print ("esto es line.qty_available_today 1---",line.qty_available_today)
				#print ("esto es line.free_qty_today 1---",line.free_qty_today)
			line.scheduled_date = line.order_id.commitment_date or line._expected_date()
			line.virtual_available_at_date = False
			treated |= line

		qty_processed_per_product = defaultdict(lambda: 0)
		grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
		for line in self.filtered(lambda l: l.state in ('draft', 'sent')):
			#print ("Ingresa en 2",line.product_id)
			#print ("Ingresa en 2.1",line.display_qty_widget)
			#if not (line.product_id and line.display_qty_widget):
			if not line.product_id:
				#print ("Ingresa donde no debe")
				continue
			grouped_lines[(line.warehouse_id.id, line.order_id.commitment_date or line._expected_date())] |= line
		#print ("Esto es grouped_lines abajo",grouped_lines)
		#Funcionalidad de Odoo base modificada
		#for (warehouse, scheduled_date), lines in grouped_lines.items():
		#	product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date, warehouse=warehouse).read([
		#		'qty_available',
		#		'free_qty',
		#		'virtual_available',
		#		])
		#	qties_per_product = {
		#		product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
		#		for product in product_qties
		#	}

		#Nueva funcionalidad permite buscar en tabla params.serie.point.sale.warehouse.
		for (warehouse, scheduled_date), lines in grouped_lines.items():
			for line in lines:
				parametros = self.env['params.serie.point.sale.warehouse'].search([('serie_id','=',line.order_id.serie_id.id),('company_id','=',line.order_id.company_id.id)])
				#print ("Esto es len de parametros",len(parametros))
				#print ("Esto es la company_id",line.order_id.company_id.id)
				#print ("Esto es la serie",line.order_id.serie_id.id)
				if len(parametros) == 1:
					almacenes = []
					for warehouse in parametros.warehouse_ids:
						if warehouse.status == True:
							almacenes.append(warehouse.warehouse_id.id)

				elif len(parametros) > 1:
					raise ValidationError("Se encontró mas de un registro de parametros de almacenes permitidos en punto de venta, por favor revisé con el administrador.")
				else:
					raise ValidationError("No se encontró un registro de parametros de almacenes permitidos en punto de venta, por favor revisé con el administrador.")

				stock_locations = self.env['stock.location'].browse(almacenes)
				qty_available_today = 0
				free_qty_today = 0
				virtual_available_at_date = 0
				for stock in stock_locations:
					quants_ids = self.env['stock.quant'].search([('location_id','=',stock.id),('product_id','=',line.product_id.id)])
					for quant in quants_ids:
						qty_available_today = qty_available_today + quant.available_quantity
						virtual_available_at_date = virtual_available_at_date + quant.available_quantity
						free_qty_today = free_qty_today + quant.quantity
				line.qty_available_today = qty_available_today
				line.free_qty_today = free_qty_today
				line.virtual_available_at_date = virtual_available_at_date


				#rint ("ESTO ES CANTIDAD DISPONIBLE HOY",qty_available_today)
				#print("ESTO ES CANTIDAD LIBRE HOY",free_qty_today)
				#print("ESTO ES CANTIDAD VIRTUAL DISPONIBLE",virtual_available_at_date)

				sales = self.env['sale.order.line'].search([('state','in',('sale','draft','sent','done')),('product_id','=',line.product_id.id),('order_id.serie_id','=',line.order_id.serie_id.id)])
				reservado = 0
				for sale in sales:
					reservado = reservado + (sale.product_uom_qty - sale.qty_delivered)
				cantidades_reservadas_total = reservado


				line.unidades_sin_reserva = line.free_qty_today - cantidades_reservadas_total
				cajas = int(line.unidades_sin_reserva/line.product_id.quantity_uom)
				botellas = line.unidades_sin_reserva - (cajas * line.product_id.quantity_uom)
				if str(line.product_id.sub_type_uom.name) == 'CAJA' and cajas > 1: 
					unidad_cajas = 'CAJAS'
				elif str(line.product_id.sub_type_uom.name) == 'CAJA' and cajas == 1: 
					unidad_cajas = 'CAJA'
				elif str(line.product_id.sub_type_uom.name) == 'CAJA' and cajas == 0: 
					unidad_cajas = 'CAJAS'
				else:
					unidad_cajas = str(line.product_id.sub_type_uom.name)
				unidad_botellas = str(line.product_id.uom_id.name)
				line.inv_available = str(cajas)+" "+ unidad_cajas+ "\n" + str(botellas) +" "+ unidad_botellas
				cantidad_reservada = 0
				for reservado in line.product_id.reserved_related_ids:
					if reservado.order_id.serie_id == line.order_id.serie_id:
						#print ("Ingresa en 5")
						#print ("Esto es reservado",reservado)
						#print ("Esto es reservado.order_id.id",reservado.order_id.id)
						#print ("Esto es line._origin.order_id.id",line._origin.order_id.id)
						#print ("Esto es importante",line.order_id.id)
						if reservado.order_id.id == line.order_id.id:
							#print ("Aqui entra a sumar el pedido",reservado.cantidad)
							cantidad_reservada = cantidad_reservada + reservado.cantidad

				#print ("Esto es cantidad_reservada",cantidad_reservada)

				#line.disponible_para_pedido = line.free_qty_today - cantidad_reservada
				line.disponible_para_pedido = line.free_qty_today - cantidades_reservadas_total + cantidad_reservada
				if line.product_uom_qty > line.disponible_para_pedido:
					#print ("Ingresa en 6")
					line.unidad = int(line.disponible_para_pedido/line.product_id.quantity_uom)
					line.sub_unidad = line.disponible_para_pedido - (line.unidad * line.product_id.quantity_uom)
					line.product_uom_qty = line.disponible_para_pedido
					self.env.user.notify_danger(message='Se ingresó una cantidad mayor a la disponible para el producto ' + str(line.product_id.name) + ' la cantidad máxima disponible para reserva es de: ' + str(line.unidad) + ' Cajas y ' + str(line.sub_unidad) + ' Unidades'  )




				line.scheduled_date = scheduled_date
				line.forecast_expected_date = False
				product_qty = line.product_uom_qty
				qty_processed_per_product[line.product_id.id] += product_qty
			treated |= lines
		remaining = (self - treated)
		remaining.virtual_available_at_date = False
		remaining.scheduled_date = False
		remaining.forecast_expected_date = False
		remaining.free_qty_today = False
		remaining.qty_available_today = False
		remaining.unidades_sin_reserva = False
		remaining.inv_available = ""

		#Funcionalidad base de Odoo comentada, modificación agregada arriba.
		'''
			for line in lines:
				#print ("Ingresa en 4")
				line.scheduled_date = scheduled_date
				qty_available_today, free_qty_today, virtual_available_at_date = qties_per_product[line.product_id.id]
				line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
				line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
				line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[line.product_id.id]
				line.forecast_expected_date = False
				product_qty = line.product_uom_qty
				#line.unidades_sin_reserva = line.free_qty_today - line.product_id.cantidades_reservadas
				line.unidades_sin_reserva = line.free_qty_today - line.product_id.product_tmpl_id.cantidades_reservadas_total
				cajas = int(line.unidades_sin_reserva/line.product_id.quantity_uom)
				botellas = line.unidades_sin_reserva - (cajas * line.product_id.quantity_uom)
				if str(line.product_id.sub_type_uom.name) == 'CAJA' and cajas > 1: 
					unidad_cajas = 'CAJAS'
				elif str(line.product_id.sub_type_uom.name) == 'CAJA' and cajas == 1: 
					unidad_cajas = 'CAJA'
				elif str(line.product_id.sub_type_uom.name) == 'CAJA' and cajas == 0: 
					unidad_cajas = 'CAJAS'
				else:
					unidad_cajas = str(line.product_id.sub_type_uom.name)
				unidad_botellas = str(line.product_id.uom_id.name)
				line.inv_available = str(cajas)+" "+ unidad_cajas+ "\n" + str(botellas) +" "+ unidad_botellas
				cantidad_reservada = 0
				for reservado in line.product_id.reserved_related_ids:
					#print ("Ingresa en 5")
					#print ("Esto es reservado",reservado)
					#print ("Esto es reservado.order_id.id",reservado.order_id.id)
					#print ("Esto es line._origin.order_id.id",line._origin.order_id.id)
					if reservado.order_id.id == line._origin.order_id.id:
						#print ("Aqui entra a sumar el pedido",reservado.cantidad)
						cantidad_reservada = cantidad_reservada + reservado.cantidad

				#print ("Esto es cantidad_reservada",cantidad_reservada)

				#line.disponible_para_pedido = line.free_qty_today - cantidad_reservada
				line.disponible_para_pedido = line.free_qty_today - line.product_id.product_tmpl_id.cantidades_reservadas_total + cantidad_reservada
				if line.product_uom_qty > line.disponible_para_pedido:
					#print ("Ingresa en 6")
					line.unidad = int(line.disponible_para_pedido/line.product_id.quantity_uom)
					line.sub_unidad = line.disponible_para_pedido - (line.unidad * line.product_id.quantity_uom)
					line.product_uom_qty = line.disponible_para_pedido
					self.env.user.notify_danger(message='Se ingresó una cantidad mayor a la disponible para el producto ' + str(line.product_id.name) + ' la cantidad máxima disponible para reserva es de: ' + str(line.unidad) + ' Cajas y ' + str(line.sub_unidad) + ' Unidades'  )
				#print ("esto es line.qty_available_today 2---",line.qty_available_today)
				#print ("esto es line.free_qty_today 2---",line.free_qty_today)
				if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
					#print ("Ingresa en 7")
					raise ValidationError('El producto:' + str(line.product_id.name) + " tiene una unidad de medida diferente a la unidad de medida de venta")
					line.qty_available_today = line.product_id.uom_id._compute_quantity(line.qty_available_today, line.product_uom)
					line.free_qty_today = line.product_id.uom_id._compute_quantity(line.free_qty_today, line.product_uom)
					line.virtual_available_at_date = line.product_id.uom_id._compute_quantity(line.virtual_available_at_date, line.product_uom)
					#line.unidades_sin_reserva = line.free_qty_today - line.product_id.cantidades_reservadas
					line.unidades_sin_reserva = line.free_qty_today - line.product_id.product_tmpl_id.cantidades_reservadas_total
					product_qty = line.product_uom._compute_quantity(product_qty, line.product_id.uom_id)
				#print ("esto es virtual_available_at_date 3---", line.virtual_available_at_date)
				#print ("esto es scheduled_date 3---", line.scheduled_date)
				#print ("esto es forecast_expected_date 3---", line.forecast_expected_date)
				#print ("esto es free_qty_today 3---", line.free_qty_today)
				#print ("esto es qty_available_today 3---", line.qty_available_today )
				qty_processed_per_product[line.product_id.id] += product_qty   



			treated |= lines
		remaining = (self - treated)
		remaining.virtual_available_at_date = False
		remaining.scheduled_date = False
		remaining.forecast_expected_date = False
		remaining.free_qty_today = False
		remaining.qty_available_today = False
		remaining.unidades_sin_reserva = False
		remaining.inv_available = ""
		'''

	@api.depends('quantity_unit','product_id')
	def _compute_quantity_unit(self):
		#print ("Ingresa tambien a _compute_quantity_unit")
		for line in self:
			if line.product_id:
				line._compute_qty_at_date()
				line.quantity_unit = str(line.product_id.quantity_uom) + " " + str(line.product_id.uom_id.name)

			if line.unidad != 0  or line.sub_unidad != 0  and line.product_uom_qty == 0 and line.state == 'draft':
				line.onchange_unidad_sub_unidad()
				reserva = self.env['reserved.product'].search([('order_id','=',line.order_id.id),('product_id','=',line.product_id.product_tmpl_id.id)])
				if line.product_uom_qty > 0 and not reserva:
					line.order_id.save_order()

	@api.onchange('unidad','sub_unidad')
	def onchange_unidad_sub_unidad(self):
		if self.product_id:
			cantidad_anterior = self.product_uom_qty
			if self.unidad >= 0:
				self.product_uom_qty = (self.unidad * self.product_id.quantity_uom) + self.sub_unidad
			if self.sub_unidad >= 0:
				if self.product_id:
					if self.sub_unidad >= self.product_id.quantity_uom:
						if self.product_id.quantity_uom == 0:
							raise ValidationError('El producto:' + str(self.product_id.name) + " en el campo cantidad por unidad de medida tiene valor de 0 debe agregar un valor valido mayor a 0")
						else:
							piezas_empaques = int(self.sub_unidad/self.product_id.quantity_uom)
						self.unidad = self.unidad + int(self.sub_unidad/self.product_id.quantity_uom)
						self.sub_unidad = self.sub_unidad - (piezas_empaques *  self.product_id.quantity_uom)

				self.product_uom_qty = (self.unidad * self.product_id.quantity_uom) + self.sub_unidad
			if self.sub_unidad < 0 or self.unidad < 0:
				raise ValidationError('No puedes vender una cantidad negativa.')
			
		
		

	def unlink(self):
		if self._check_line_unlink():
			raise UserError(_('You can not remove an order line once the sales order is confirmed.\nYou should rather set the quantity to 0.'))
		for line in self:
			line.product_id.cantidades_reservadas = line.product_id.cantidades_reservadas - line.product_uom_qty
			reserva =  self.env['reserved.product'].search([('order_id','=',line.order_id.id),('product_id','=',line.product_id.product_tmpl_id.id)])
			if reserva:
				reserva.unlink()
		return super(SaleOrderLine, self).unlink()

	def _prepare_invoice_line(self, **optional_values):
		#print("Esto es context en _prepare_invoice_line",self.env.context)
		self.ensure_one()
		unidad = (self.env.context.get('product_qty') / self.product_id.quantity_uom)
		sub_unidad = self.env.context.get('product_qty') - (unidad * self.product_id.quantity_uom)
		res = {
		    'display_type': self.display_type,
		    'sequence': self.env.context.get('sequence_invoice'),
		    'name': self.name,
		    'product_id': self.product_id.id,
		    'product_uom_id': self.product_uom.id,
		    'quantity': self.env.context.get('product_qty'),
		    'discount': self.discount,
		    'price_unit': self.price_unit,
		    'tax_ids': [(6, 0, self.tax_id.ids)],
		    'analytic_account_id': self.order_id.analytic_account_id.id,
		    'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
		    'sale_line_ids': [(4, self.id)],
		    #'l10n_mx_edi_customs_number': self.env.context.get('pedimento'),
		    'unidad': unidad,
		    'sub_unidad': sub_unidad
		}
		#print ("Esto es optional_values",optional_values)
		if optional_values:
		    res.update(optional_values)
		if self.display_type:
		    res['account_id'] = False
		return res

	@api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
	def _compute_amount(self):
		for line in self:
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
			taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
			price_subtotal_base = taxes['total_excluded']
			for tax in taxes.get('taxes', []):
				if tax['tax_ids'] == []:
					#print("INGRESA AL IF")
					price_subtotal_base = tax['base']
				else:
					#print("INGRESA AL ELSE")
					price_subtotal_base = tax['base']
			line.update({
				'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
				'price_total': taxes['total_included'],
				'price_subtotal': taxes['total_excluded'],
				'price_subtotal_base': price_subtotal_base,
				})
			if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
				line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])


	@api.onchange('product_id')
	def product_id_change(self):
		domain = super(SaleOrderLine, self).product_id_change()
		if self.product_id:
			if not self.order_id.partner_id:
				raise ValidationError(_('No ah seleccionado el cliente.'))
			if not self.order_id.serie_id:
				raise ValidationError(_('No ah seleccionado la serie para el pedido.'))
			self.grados_alcohol = self.product_id.grados_alcohol
			self.contenido = self.product_id.contenido
			self.quantity_unit = str(self.product_id.quantity_uom) + " " + str(self.product_id.uom_id.name)
			self.pricelist_id = self.order_id.pricelist_id.id
			#pendiente
			tarifa = self.env['product.pricelist.item'].search([('product_tmpl_id','=',self.product_id.product_tmpl_id.id),('pricelist_id','=',self.pricelist_id.id)])
			if tarifa:
				self.box_price = tarifa.price_unidad
			else:
				self.box_price = 0 
		else:
			self.quantity_unit = ""

		self.product_uom_qty = 0
		self.unidad = 0
		self.sub_unidad = 0

	@api.depends('price_subtotal', 'tax_id')
	def _compute_sale_taxes_by_line(self):
		for linea in self:
			taxes_dict = {}
			if len(linea.tax_id) > 0 and linea.product_id:
				contador = 0
				bandera = False
				for ltax_ in linea.tax_id:
					contador = contador + 1
					if ltax_.include_base_amount == True and linea.price_subtotal != linea.price_subtotal_base and contador == 1:
						if ltax_.amount != 0:
							ltax = (ltax_.amount) / 100
						else:
							ltax = 0
						taxes_dict.update({
							ltax_.amount: {
							'base': linea.price_subtotal,
							'monto': linea.price_subtotal * ltax,
							'impuesto': ltax_.name,
							}
						})
						bandera = True
					elif bandera == True:
						if ltax_.amount != 0:
							ltax = (ltax_.amount) / 100
						else:
							ltax = 0
						taxes_dict.update({
							ltax_.amount: {
							'base': linea.price_subtotal_base,
							'monto': linea.price_subtotal_base * ltax,
							'impuesto': ltax_.name,
							}
						})
					else:
						if ltax_.amount != 0:
							ltax = (ltax_.amount) / 100
						else:
							ltax = 0
						taxes_dict.update({
							ltax_.amount: {
							'base': linea.price_subtotal,
							'monto': linea.price_subtotal * ltax,
							'impuesto': ltax_.name,
							}
						})
				linea.taxes_by_group = json.dumps(taxes_dict)
			else:
				linea.taxes_by_group = False