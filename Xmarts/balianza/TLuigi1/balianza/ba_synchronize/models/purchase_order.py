# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from dateutil.relativedelta import relativedelta
import json

#Modificaciones para tener control de gastos relacionados, calculo de impuestos, y control en cajas y unidades.
class PurchaseOrder(models.Model):

	_inherit='purchase.order'

	taxes_by_group = fields.One2many('purchase.line.tax', 'purchase_related_id', store=True)
	landed_cost_related = fields.One2many('stock.landed.cost', 'purchase_related_id', string="Gastos relacionados")
	landed_cost_line_related = fields.One2many('stock.landed.cost.lines', 'purchase_related_id', string="Lineas de gastos relacionados")
	pickings_ids = fields.One2many('stock.picking', 'purchase_id', string="Movimientos")

	def save_order(self):
		#print ("Se guardo registro pedido de compra")
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
				registros = self.env['purchase.line.tax'].search([('purchase_related_id', '=', self._origin.id)])
				registros.unlink()
			if order.order_line:
				registros = self.env['purchase.line.tax'].search([('purchase_related_id', '=', self._origin.id)])
				if registros:
					registros.unlink()
				for (key1, val1) in unico_impuesto.items():
					#print("Pasa aqui al final",key1)
					#print("Pasa aqui al final val1",val1)
					values = {
						'name':val1['nombre'],
						'monto_base':round(val1['base'],4),
						'total_impuesto':round(val1['monto'], 4) ,
						'purchase_related_id':self._origin.id,
					} 
					self.env['purchase.line.tax'].create(values)


			#print ("Esto es unico_impuesto",unico_impuesto)

	def write(self, values):
		#print ("Esto es self en write PO",self)
		result = super(PurchaseOrder, self).write(values)
		self.save_order()
		return result

	@api.model
	def create(self, vals):
		#print ("Esto es self en create PO",self)
		result = super(PurchaseOrder, self).create(vals)
		result.save_order()
		return result



	@api.onchange('order_line')
	def onchange_order_line(self):
		product = []
		for order in self.order_line:
			#print ("Entra al onchange order_line",order.product_id)
			if order.product_id in product:
				raise ValidationError("El producto: " + str(order.product_id.name) + " ya se encuentra agregado al pedido.")
			else:
				product.append(order.product_id)

	@api.depends('order_line.price_total')
	def _amount_all(self):
		#print("Esto es _amount_all",self.env.context)
		for order in self:
			amount_untaxed = amount_tax = 0.0
			
			for line in order.order_line:
				line._compute_amount()
				amount_untaxed += line.price_subtotal
				amount_tax += line.price_tax

			order.update({
				'amount_untaxed': order.currency_id.round(amount_untaxed),
				'amount_tax': order.currency_id.round(amount_tax),
				'amount_total': amount_untaxed + amount_tax,
				})

	def action_create_expense(self):
		self.ensure_one()
		return {
			'name': _('Crear Gasto'),
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.landed.cost',
			'view_id': self.env.ref('gm_import_expenses_pediments.view_stock_landed_cost_gm').id,
			'type': 'ir.actions.act_window',
			'context': {'default_purchase_order_id':self.id},
			'target': 'new'
			}

class PurchaseOrderLine(models.Model):

	_inherit='purchase.order.line'

	quantity_unit = fields.Char(string="Unidades por empaque", compute="_compute_quantity_unit", store=True)
	price_subtotal_base = fields.Float(string="Subtotal base para IVA",compute="_compute_amount", store=True)
	taxes_by_group = fields.Char("Grupo de impuestos", compute="_compute_purchase_taxes_by_line", store=True)
	unidad  = fields.Integer(string="Cajas", default = 0)
	sub_unidad = fields.Integer(string="Unidades", default = 0)
	unidad_sc  = fields.Integer(string="Cajas sin cargo", default = 0)
	sub_unidad_sc = fields.Integer(string="Unidades sin cargo", default = 0)
	cantidad = fields.Float(string="Cantidad", related='product_qty')
	qty_received_unidad = fields.Integer(string="Cajas recibidas", default = 0)
	qty_received_sub_unidad = fields.Integer(string="Unidades recibidas", default = 0)
	qty_received_unidad_sc = fields.Integer(string="Cajas recibidas SC", default = 0)
	qty_received_sub_unidad_sc = fields.Integer(string="Unidades recibidas SC", default = 0)
	grados_alcohol = fields.Float(string="Grados alcohol", default = 0)
	contenido = fields.Integer(string="Contenido", default = 0)
	box_price = fields.Float(string="Precio caja")


	def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
		self.ensure_one()
		product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
		description_picking = product._get_description(self.order_id.picking_type_id)
		if self.product_description_variants:
			description_picking += "\n" + self.product_description_variants
		date_planned = self.date_planned or self.order_id.date_planned
		return {
			'name': (self.name or '')[:2000],
			'product_id': self.product_id.id,
			'date': date_planned,
			'date_deadline': date_planned + relativedelta(days=self.order_id.company_id.po_lead),
			'location_id': self.order_id.partner_id.property_stock_supplier.id,
			'location_dest_id': (self.orderpoint_id and not (self.move_ids | self.move_dest_ids)) and self.orderpoint_id.location_id.id or self.order_id._get_destination_location(),
			'picking_id': picking.id,
			'partner_id': self.order_id.dest_address_id.id,
			'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
			'state': 'draft',
			'purchase_line_id': self.id,
			'company_id': self.order_id.company_id.id,
			'price_unit': price_unit,
			'picking_type_id': self.order_id.picking_type_id.id,
			'group_id': self.order_id.group_id.id,
			'origin': self.order_id.name,
			'description_picking': description_picking,
			'propagate_cancel': self.propagate_cancel,
			'route_ids': self.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.order_id.picking_type_id.warehouse_id.route_ids])] or [],
			'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
			'product_uom_qty': product_uom_qty,
			'demand_cc': (self.unidad * self.product_id.quantity_uom) + self.sub_unidad,
			'demand_sc': (self.unidad_sc * self.product_id.quantity_uom) + self.sub_unidad_sc,
			'unidad': self.unidad,
			'sub_unidad': self.sub_unidad,
			'unidad_sc': self.unidad_sc,
			'sub_unidad_sc':self.sub_unidad_sc,
			'product_uom': product_uom.id,
		}

	def _get_stock_move_price_unit(self):
		self.ensure_one()
		line = self[0]
		order = line.order_id
		price_unit = line.price_unit
		if line.taxes_id:
			if line.product_id.costing_method == 'total_included':
				price_unit = line.taxes_id.with_context(round=False).compute_all(
					price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id, partner=line.order_id.partner_id
					)['total_included']
			if line.product_id.costing_method == 'total_excluded':
				price_unit = line.taxes_id.with_context(round=False).compute_all(
					price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id, partner=line.order_id.partner_id
					)['total_excluded']
			if line.product_id.costing_method == 'total_void':
				price_unit = line.taxes_id.with_context(round=False).compute_all(
					price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id, partner=line.order_id.partner_id
					)['total_void']

			#print ("Esto es price_unit que busco",line.taxes_id.with_context(round=False).compute_all(
			#		price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id, partner=line.order_id.partner_id
			#		))
		if line.product_uom.id != line.product_id.uom_id.id:
			price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
		if order.currency_id != order.company_id.currency_id:
			price_unit = order.currency_id._convert(
				price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(), round=False)
		return price_unit


	@api.depends('quantity_unit','product_id')
	def _compute_quantity_unit(self):
		for line in self:
			if line.product_id:
				line.quantity_unit = str(line.product_id.quantity_uom) + " " + str(line.product_id.uom_id.name)


	@api.onchange('unidad','sub_unidad','unidad_sc','sub_unidad_sc')
	def onchange_unidad_sub_unidad(self):
		if self.unidad >= 0:
			self.product_qty = (self.unidad * self.product_id.quantity_uom) + self.sub_unidad + (self.unidad_sc * self.product_id.quantity_uom) + self.sub_unidad_sc
		if self.sub_unidad >= 0:
			if self.product_id:
				if self.sub_unidad >= self.product_id.quantity_uom:
					piezas_empaques = int(self.sub_unidad/self.product_id.quantity_uom)
					self.unidad = self.unidad + int(self.sub_unidad/self.product_id.quantity_uom)
					self.sub_unidad = self.sub_unidad - (piezas_empaques *  self.product_id.quantity_uom)
		if self.sub_unidad_sc >= 0:
			if self.product_id:
				if self.sub_unidad_sc >= self.product_id.quantity_uom:
					piezas_empaques_sc = int(self.sub_unidad_sc/self.product_id.quantity_uom)
					self.unidad_sc = self.unidad + int(self.sub_unidad_sc/self.product_id.quantity_uom)
					self.sub_unidad_sc = self.sub_unidad_sc - (piezas_empaques_sc *  self.product_id.quantity_uom)

		self.product_qty = (self.unidad * self.product_id.quantity_uom) + self.sub_unidad + (self.unidad_sc * self.product_id.quantity_uom) + self.sub_unidad_sc
		if self.sub_unidad < 0 or self.unidad < 0:
			raise ValidationError('No puedes vender una cantidad negativa.')
		

	def _prepare_compute_all_values(self):
		self.ensure_one()
		return {
			'price_unit': self.price_unit,
			'currency_id': self.order_id.currency_id,
			'product_qty': self.product_qty - ((self.unidad_sc * self.product_id.quantity_uom) + self.sub_unidad_sc),
			'product': self.product_id,
			'partner': self.order_id.partner_id,
		}


	@api.depends('product_qty', 'price_unit', 'taxes_id')
	def _compute_amount(self):
		for line in self:
			vals = line._prepare_compute_all_values()
			#print("Esto es vals['product_qty']",vals['product_qty'])
			taxes = line.taxes_id.compute_all(
				vals['price_unit'],
				vals['currency_id'],
				vals['product_qty'],
				vals['product'],
				vals['partner'])
			#print ("Esto es taxes",taxes)
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


	@api.depends('price_subtotal', 'taxes_id')
	def _compute_purchase_taxes_by_line(self):
		for linea in self:
			taxes_dict = {}
			if len(linea.taxes_id) > 0 and linea.product_id:
				contador = 0
				bandera = False
				for ltax_ in linea.taxes_id:
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
	


	

	@api.onchange('product_id')
	def onchange_product_id(self):
		domain = super(PurchaseOrderLine, self).onchange_product_id()

		if self.product_id:
			self.grados_alcohol = self.product_id.grados_alcohol
			self.contenido = self.product_id.contenido
			self.quantity_unit = str(self.product_id.quantity_uom) + " " + str(self.product_id.uom_id.name)
		else:
			self.quantity_unit = ""
			self.grados_alcohol = 0
			self.contenido = 0
		self.product_qty = 0

	@api.onchange('box_price','price_unit')
	def onchange_box_price_unit(self):
		if self.box_price:
			self.price_unit = round(self.box_price/ self.product_id.quantity_uom,4)
		if self.price_unit:
			self.box_price = round(self.price_unit * self.product_id.quantity_uom,2)

		

		

	@api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
	def _compute_qty_received(self):
		super(PurchaseOrderLine, self)._compute_qty_received()
		for line in self:
			if line.qty_received_method == 'stock_moves':
				total = 0.0
				sum_qty = 0
				sum_qty_sc = 0
				for move in line.move_ids.filtered(lambda m: m.product_id == line.product_id):
					#print ("Recorre move",move)
					if move.state == 'done' and move.picking_type_id.code == 'incoming':
						if move.location_dest_id.usage == "supplier":
							if move.to_refund:
								#print ("Esto es move en if == supplier",move)
								total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)

								for move_line in move.move_line_ids:
									if move_line.no_charge_cost == True:
										sum_qty_sc = sum_qty_sc + move_line.qty_done
									else:
										sum_qty = sum_qty + move_line.qty_done
						elif move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned():
							pass
						elif (
							move.location_dest_id.usage == "internal"
							and move.to_refund
							and move.location_dest_id
							not in self.env["stock.location"].search(
							[("id", "child_of", move.warehouse_id.view_location_id.id)]
							)
						):
							total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
						else:
							#print ("Esto es move en else",move)
							total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
							for move_line in move.move_line_ids:
								if move_line.no_charge_cost == True:
									sum_qty_sc = sum_qty_sc + move_line.qty_done
								else:
									sum_qty = sum_qty + move_line.qty_done
				line._track_qty_received(total)
				line.qty_received = total
				line.qty_received_unidad = int(sum_qty / line.product_id.quantity_uom)
				line.qty_received_sub_unidad = sum_qty - (line.qty_received_unidad * line.product_id.quantity_uom)
				line.qty_received_unidad_sc = int(sum_qty_sc / line.product_id.quantity_uom)
				line.qty_received_sub_unidad_sc = sum_qty_sc - (line.qty_received_unidad_sc * line.product_id.quantity_uom)



