# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from operator import itemgetter
from re import findall as regex_findall
from re import split as regex_split

from dateutil import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round
from odoo.tools.misc import format_date, OrderedSet

PROCUREMENT_PRIORITIES = [('0', 'Normal'), ('1', 'Urgent')]
from odoo.exceptions import UserError, RedirectWarning, ValidationError

#Modificaciones que permiten el control en cajas y unidades, control de mercancia con cargo y sin cargo.

class StockMove(models.Model):

	_inherit='stock.move'

	trans_interna = fields.Boolean(string="Es una transferencia interna?", readonly=True, default=False)
	unidad  = fields.Integer(string="Cajas")
	sub_unidad = fields.Integer(string="Unidades")
	unidad_sc  = fields.Integer(string="Cajas sin cargo")
	sub_unidad_sc = fields.Integer(string="Unidades sin cargo")
	demand_cc  = fields.Integer(string="Demanda con cargo")
	demand_sc  = fields.Integer(string="Demanda sin cargo")


	def _get_price_unit(self):
		""" Returns the unit price to value this stock move """
		self.ensure_one()
		price_unit = self.price_unit
		# If the move is a return, use the original move's price unit.
		if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
			price_unit = self.origin_returned_move_id.sudo().stock_valuation_layer_ids[-1].unit_cost
		#print ("Price_unit buscado",price_unit)
		#print ("Self.product_id.standard_price", self.product_id.standard_price)
		return not self.company_id.currency_id.is_zero(price_unit) and price_unit or self.product_id.standard_price

	@api.depends('move_line_ids.product_qty')
	def _compute_reserved_availability(self):
		for move in self:
			if move.purchase_line_id and move.picking_id.picking_type_id.code == 'incoming':
				#print ("INGRESA CUANDO ES DE COMPRA")
				moves = self.env['stock.move'].search([('purchase_line_id','=', move.purchase_line_id.id),('picking_id.picking_type_id.code','=','incoming'),('product_id','=',move.product_id.id),('state','=','done')])
				if move.state == 'done':
					qty_sc = 0
					qty_cc = 0
					for move_id in move.move_line_ids:
						if move_id.no_charge_cost == True:
							qty_sc = qty_sc + move_id.qty_done
						else:
							qty_cc = qty_cc + move_id.qty_done
					move.unidad = int(qty_cc / move.product_id.quantity_uom)
					move.sub_unidad = qty_cc - (move.unidad * move.product_id.quantity_uom)
					move.unidad_sc = int(qty_sc / move.product_id.quantity_uom)
					move.sub_unidad_sc = qty_sc - (move.unidad_sc * move.product_id.quantity_uom)

				elif move.state == 'assigned' and moves:
					sum_unidad = 0
					sum_sub_unidad = 0
					sum_unidad_sc = 0
					sum_sub_unidad_sc = 0
					for move_line in moves:
						sum_unidad = sum_unidad + move_line.unidad
						sum_sub_unidad = sum_sub_unidad + move_line.sub_unidad
						sum_unidad_sc = sum_unidad_sc + move_line.unidad_sc
						sum_sub_unidad_sc = sum_sub_unidad_sc + move_line.sub_unidad_sc

					qty_sc = move.demand_sc - ((sum_unidad_sc * move.product_id.quantity_uom) + sum_sub_unidad_sc)
					qty_cc = move.demand_cc - ((sum_unidad * move.product_id.quantity_uom) + sum_sub_unidad)
					move.unidad = int(qty_cc / move.product_id.quantity_uom)
					move.sub_unidad = qty_cc - (move.unidad * move.product_id.quantity_uom)
					move.unidad_sc = int(qty_sc / move.product_id.quantity_uom)
					move.sub_unidad_sc = qty_sc - (move.unidad_sc * move.product_id.quantity_uom)



			elif move.sale_line_id and move.picking_id.picking_type_id.code == 'outgoing':
				#print ("INGRESA CUANDO ES DE VENTA")
				move.unidad = int(move.product_uom_qty / move.product_id.quantity_uom)
				if move.unidad > 0:
					move.sub_unidad = move.product_uom_qty - (move.unidad *  move.product_id.quantity_uom)
				else:
					move.sub_unidad = move.product_uom_qty
				move.unidad_sc = 0
				move.sub_unidad_sc = 0

		if not any(self._ids):
			#print ("Ingresa al if despues")
			for move in self:
				reserved_availability = sum(move.move_line_ids.mapped('product_qty'))
				move.reserved_availability = move.product_id.uom_id._compute_quantity(
					reserved_availability, move.product_uom, rounding_method='HALF-UP')
				#print ("Dentro del if esto es reserved_availability",move.reserved_availability)
		else:
			result = {data['move_id'][0]: data['product_qty'] for data in
				self.env['stock.move.line'].read_group([('move_id', 'in', self.ids)], ['move_id', 'product_qty'], ['move_id'])}
			for move in self:
				move.reserved_availability = move.product_id.uom_id._compute_quantity(
					result.get(move.id, 0.0), move.product_uom, rounding_method='HALF-UP')
				#print ("Dentro del if esto es reserved_availability",move.reserved_availability)

	def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
		#print ("Esto es self",self.state)
		self.ensure_one()
		if not lot_id:
			lot_id = self.env['stock.production.lot']
		if not package_id:
			package_id = self.env['stock.quant.package']
		if not owner_id:
			owner_id = self.env['res.partner']

		taken_quantity = min(available_quantity, need)
		#print ("Pasa en 1", taken_quantity)

		if not strict and self.product_id.uom_id != self.product_uom:
			#print ("Pasa en 2")
			taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
			taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

		quants = []
		rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')

		if self.product_id.tracking == 'serial':
			#print ("Pasa en 3")
			if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
				taken_quantity = 0

		try:
			#print ("Pasa en 4")
			with self.env.cr.savepoint():
				if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
					#print ("Pasa en 5")
					quants = self.env['stock.quant']._update_reserved_quantity(
		                self.product_id, location_id, taken_quantity, lot_id=lot_id,
		                package_id=package_id, owner_id=owner_id, strict=strict, sale_id = self.sale_line_id.order_id
		            )
		except UserError:
			taken_quantity = 0

		#print ("Esto es quants que busco",quants)
		for reserved_quant, quantity in quants:
			#print ("Esto es reserved_quant",reserved_quant)
			#print ("Esto es quantity",quantity)

			moves = self.move_line_ids.filtered(lambda ml: ml._reservation_is_updatable(quantity, reserved_quant))
			#print ("Esto es moves",moves)
			if moves:
				to_update = moves.search([('stock_quant_id','=',reserved_quant.id)])
				#print ("Esto es to_update",to_update)
			else:
				to_update = self.move_line_ids.filtered(lambda ml: ml._reservation_is_updatable(quantity, reserved_quant))
				#print ("Esto es to_update original",to_update)

			if to_update:
				#print ("Pasa en 6",to_update)
				uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update[0].product_uom_id, rounding_method='HALF-UP')
				uom_quantity = float_round(uom_quantity, precision_digits=rounding)
				uom_quantity_back_to_product_uom = to_update[0].product_uom_id._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
			if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
				#print ("Pasa en 7")
				to_update[0].with_context(bypass_reservation_update=True).product_uom_qty += uom_quantity
			else:
				if self.product_id.tracking == 'serial':
					#print ("Pasa en 8")
					for i in range(0, int(quantity)):
						self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant))
				else:
					#print ("Pasa en 9")
					move = self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
					move.write({'stock_quant_id':reserved_quant.id})
		return taken_quantity

	def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
		self.ensure_one()
		#print ("pasa a _prepare_move_line_vals")
		# apply putaway
		location_dest_id = self.location_dest_id._get_putaway_strategy(self.product_id).id or self.location_dest_id.id
		vals = {
		    'move_id': self.id,
		    'product_id': self.product_id.id,
		    'product_uom_id': self.product_uom.id,
		    'location_id': self.location_id.id,
		    'location_dest_id': location_dest_id,
		    'picking_id': self.picking_id.id,
		    'company_id': self.company_id.id,
		}
		if quantity:
		    rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		    uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
		    uom_quantity = float_round(uom_quantity, precision_digits=rounding)
		    uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
		    if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
		    	#print ("Ingresa arriba",uom_quantity)
		    	vals = dict(vals, product_uom_qty=uom_quantity)
		    else:
		    	#print ("Ingresa abajo",quantity)
		    	vals = dict(vals, product_uom_qty=quantity, product_uom_id=self.product_id.uom_id.id)
		if reserved_quant:
			vals = dict(
		        vals,
		        location_id=reserved_quant.location_id.id,
		        lot_id=reserved_quant.lot_id.id or False,
		        package_id=reserved_quant.package_id.id or False,
		        owner_id =reserved_quant.owner_id.id or False,
		        )
		return vals

	def _action_assign(self):

		StockMove = self.env['stock.move']
		assigned_moves_ids = OrderedSet()
		partially_available_moves_ids = OrderedSet()
		reserved_availability = {move: move.reserved_availability for move in self}
		roundings = {move: move.product_id.uom_id.rounding for move in self}
		move_line_vals_list = []
		#print ("Ingresa a _action_assign")
		for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
			#print("Moveeee",reserved_availability[move])
			rounding = roundings[move]
			missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
			missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
			if move._should_bypass_reservation():
				#print("Moveeee1")
				if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
					for i in range(0, int(missing_reserved_quantity)):
						#print("Moveee2")
						move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
				else:
					#print("Moveeee3")
					to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
						ml.location_id == move.location_id and
						ml.location_dest_id == move.location_dest_id and
						ml.picking_id == move.picking_id and
						not ml.lot_id and
						not ml.package_id and
						not ml.owner_id)
					if to_update:
						#print("Moveee4")
						to_update[0].product_uom_qty += missing_reserved_uom_quantity
					else:
						#print("Moveeee5")
						move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
				assigned_moves_ids.add(move.id)
			else:
				#print("Moveeee6")
				if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
					#print("Moveeee7")
					assigned_moves_ids.add(move.id)
				elif not move.move_orig_ids:
					#print("Moveeee8")
					if move.procure_method == 'make_to_order':
						continue
					# If we don't need any quantity, consider the move assigned.
					#print ("missing_reserved_quantity10",missing_reserved_quantity)
					need = missing_reserved_quantity
					if float_is_zero(need, precision_rounding=rounding):
						#print("Moveeee9")
						assigned_moves_ids.add(move.id)
						continue
					# Reserve new quants and create move lines accordingly.
					forced_package_id = move.package_level_id.package_id or None
					#print ("forced_package_id10",forced_package_id)
					available_quantity = move._get_available_quantity(move.location_id, package_id=forced_package_id)
					#print ("available_quantity10",available_quantity)
					if available_quantity <= 0:
						continue
					taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
					#print ("taken_quantity10",taken_quantity)
					#print("Moveeee10.1")
					if float_is_zero(taken_quantity, precision_rounding=rounding):
						#print("Moveeee10.2")
						continue
					if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
						#print("Moveeee10.3")
						assigned_moves_ids.add(move.id)
						#print ("assigned_moves_ids", assigned_moves_ids)
					else:
						#print("Moveeee10.4")
						partially_available_moves_ids.add(move.id)
				else:
					#print("Moveeee11")
					move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
					keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

					def _keys_in_sorted(ml):
						return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

					grouped_move_lines_in = {}
					for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
						qty_done = 0
						for ml in g:
							qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
						grouped_move_lines_in[k] = qty_done
					move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move)\
						.filtered(lambda m: m.state in ['done'])\
						.mapped('move_line_ids')
					moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
					moves_out_siblings_to_consider = moves_out_siblings & (StockMove.browse(assigned_moves_ids) + StockMove.browse(partially_available_moves_ids))
					reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
					move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
					keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

					def _keys_out_sorted(ml):
					    return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

					grouped_move_lines_out = {}
					#print("Moveeee12")
					for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
					    qty_done = 0
					    for ml in g:
					        qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
					    grouped_move_lines_out[k] = qty_done
					for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
					    grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
					available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
					# pop key if the quantity available amount to 0
					available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)

					if not available_move_lines:
					    continue
					for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
						#print("Moveeee13")
						if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
							available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty
					#print ("Esto es available_move_lines",available_move_lines)
					for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
						#print("Moveeee14")
						need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
						available_quantity = move._get_available_quantity(location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
						if float_is_zero(available_quantity, precision_rounding=rounding):
						    continue
						taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity), location_id, lot_id, package_id, owner_id)
						if float_is_zero(taken_quantity, precision_rounding=rounding):
						    continue
						if float_is_zero(need - taken_quantity, precision_rounding=rounding):
						    assigned_moves_ids.add(move.id)
						    break
						partially_available_moves_ids.add(move.id)
			if move.product_id.tracking == 'serial':
				move.next_serial_count = move.product_uom_qty

		#print ("move_line_vals_list",move_line_vals_list)
		self.env['stock.move.line'].create(move_line_vals_list)
		StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
		StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
		self.mapped('picking_id')._check_entire_pack()


	def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
		self.ensure_one()
		return self.env['stock.quant']._get_available_quantity(self.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, allow_negative=allow_negative, sale_id = self.sale_line_id.order_id)

	@api.onchange('product_id')
	def onchange_product_id(self):
		if self.purchase_line_id != False and self.picking_id.state != 'draft' and self.picking_type_id.code != 'outgoing':
			raise ValidationError('No puedes agregar más a productos a los requeridos por la orden de compra.')
		if self.picking_id.state != 'draft' and self.picking_type_id.code == 'outgoing':
			raise ValidationError('No puedes agregar más a productos a los requeridos en el pedido de venta.')

		product = self.product_id.with_context(lang=self._get_lang())
		self.name = product.partner_ref
		self.product_uom = product.uom_id.id


	#@api.depends('unidad', 'sub_unidad')
	#def _compute_unidad_sub_unidad(self):
	#	for move in self:
	#		if move.purchase_line_id:
	#			move.unidad = move.purchase_line_id.unidad
	#			move.sub_unidad = move.purchase_line_id.sub_unidad
	#			move.unidad_sc = move.purchase_line_id.unidad_sc
	#			move.sub_unidad_sc = move.purchase_line_id.sub_unidad_sc
	#		elif move.sale_line_id:
	#			move.unidad = int(move.product_uom_qty / move.product_id.quantity_uom)
	#			if move.unidad > 0:
	#				move.sub_unidad = move.product_uom_qty - (move.unidad *  move.product_id.quantity_uom)
	#			else:
	#				move.sub_unidad = move.product_uom_qty
	#			move.unidad_sc = 0
	#			move.sub_unidad_sc = 0
	#		else:
	#			move.unidad = 0
	#			move.sub_unidad = 0
	#			move.unidad_sc = 0
	#			move.sub_unidad_sc = 0

	
	def write(self, vals):
		for move in self:
			if not move.purchase_line_id and move.origin and not move.sale_line_id:
				purchase_line_id = move.env['purchase.order.line'].search([('order_id.name','=',move.origin),('product_id','=',move.product_id.id)])
				for purchase in purchase_line_id:
					if purchase:
						vals['purchase_line_id'] = purchase.id
						vals['trans_interna'] = True
	
		receipt_moves_to_reassign = self.env['stock.move']
		if 'product_uom_qty' in vals:
			for move in self.filtered(lambda m: m.state not in ('done', 'draft') and m.picking_id):
			    if float_compare(vals['product_uom_qty'], move.product_uom_qty, precision_rounding=move.product_uom.rounding):
			        self.env['stock.move.line']._log_message(move.picking_id, move, 'stock.track_move_template', vals)
			if self.env.context.get('do_not_unreserve') is None:
			    move_to_unreserve = self.filtered(
			        lambda m: m.state not in ['draft', 'done', 'cancel'] and float_compare(m.reserved_availability, vals.get('product_uom_qty'), precision_rounding=m.product_uom.rounding) == 1
			    )
			    move_to_unreserve._do_unreserve()
			    (self - move_to_unreserve).filtered(lambda m: m.state == 'assigned').write({'state': 'partially_available'})
			    # When editing the initial demand, directly run again action assign on receipt moves.
			    receipt_moves_to_reassign |= move_to_unreserve.filtered(lambda m: m.location_id.usage == 'supplier')
			    receipt_moves_to_reassign |= (self - move_to_unreserve).filtered(lambda m: m.location_id.usage == 'supplier' and m.state in ('partially_available', 'assigned'))
		if 'date_deadline' in vals:
		    self._set_date_deadline(vals.get('date_deadline'))
		res = super(StockMove, self).write(vals)
		if receipt_moves_to_reassign:
		    receipt_moves_to_reassign._action_assign()
		
		return res
		
class StockMoveLine(models.Model):

	_inherit='stock.move.line'

	#api.constrains('product_uom_qty')
	#def _check_reserved_done_quantity(self):
	#	for move_line in self:
	#		#print ("Esto es move_line.state",move_line.state)
	#		if move_line.state == 'done' and not float_is_zero(move_line.product_uom_qty, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure')):
	#			#pendiente
	#			raise ValidationError(_('No se pudo generar la reserva en automatico, por favor intente realizarlo manualmente'))

	@api.depends('stock_quant_ids')
	def _compute_stock_available_ba(self):
		#print("Esto es self en _compute_stock_available_ba",self)
		for move_line in self:
			#print ("Esto es move_line",move_line.picking_id.picking_type_id.code)
			if move_line.picking_id.picking_type_id.code != 'incoming':
				quant_list = []
				if move_line.picking_id.picking_type_id.code == 'internal':
					if move_line.picking_id.purchase_id:
						#print ("Ingresa a If")
						quants = self.env['stock.quant'].search([('location_id','=',move_line.location_id.id),('lot_id.purchase_order_ids','in',move_line.picking_id.purchase_id.id),('quantity','>',0),('product_id','=',move_line.product_id.id)])
					else:
						#print("Entra a else")
						quants = self.env['stock.quant'].search([('location_id','=',move_line.location_id.id),('quantity','>',0),('product_id','=',move_line.product_id.id)])
					for quant in quants:
						quant_list.append(quant.id)
				warehouse_list = []
				if move_line.picking_id.picking_type_id.code == 'outgoing':
					quants = self.env['stock.quant'].search([('location_id','=',move_line.location_id.id),('quantity','>',0),('product_id','=',move_line.product_id.id)])

					#print("Esto es quants",quants)
					for quant in quants:
						if quant.reserved_quantity < quant.quantity:
							quant_list.append(quant.id)

					parametros = self.env['params.serie.point.sale.warehouse'].search([('serie_id','=',move_line.picking_id.sale_id.serie_id.id),('company_id','=',move_line.picking_id.company_id.id)])
					
					for warehouse in parametros.warehouse_ids:
						if warehouse.status == True:
							warehouse_list.append(warehouse.warehouse_id.id)



				#print ("Esto es quant_list",quant_list)
				if quant_list == '[]':
					#print ("Ingresa a if abajo")
					move_line.stock_quant_ids = False
				else:
					#print ("Ingresa a else abajo")
					move_line.stock_quant_ids = [(6,0, quant_list)]	

				if warehouse_list == '[]':
					#print ("Ingresa a if abajo")
					move_line.warehouse_ids = False
				else:
					#print ("Ingresa a else abajo")
					move_line.warehouse_ids = [(6,0, warehouse_list)]	

			else:
				move_line.stock_quant_ids = False
				move_line.warehouse_ids = False

	@api.depends('stock_product_ids')
	def _compute_products_stock(self):
		#print ("Ingresa a _compute_products_stock")
		list_products = []
		if self.picking_id.picking_type_id.code != 'incoming' :
			#print("ingresa al _compute_products")
			#print("Esto es self.move_line_ids_without_package",self.picking_id.move_ids_without_package)
			#print("Esto es len",len(self.picking_id.move_ids_without_package))
			if len(self.picking_id.move_ids_without_package) >= 1:
				#print("Ingresa al if")
				for move in self.picking_id.move_ids_without_package:
					if move.product_id.id not in list_products:
						#print("Esto es move.product_id",move.product_id)
						list_products.append(move.product_id.id)
				#print ("Esto es list_products",list_products)
				self.stock_product_ids = [(6,0, list_products)]	
				#print ("Esto lo que busco al final",self.stock_product_ids)	
			else:
				#print ("Ingresa a else")
				self.stock_product_ids = False
		else:
			#print("Ingresa al else abajo")
			self.stock_product_ids = False


	warehouse_ids = fields.Many2many('stock.location')
	stock_quant_ids = fields.Many2many('stock.quant', compute="_compute_stock_available_ba")
	stock_quant_id = fields.Many2one('stock.quant',string="Movimiento Kardex relacionado de almacen",ondelete='restrict')
	qty_unidad = fields.Integer(string="Cajas requeridas", compute="_compute_product_qty")
	qty_sub_unidad =fields.Integer(string="Unidades requeridas", compute="_compute_product_qty")
	unidad  = fields.Integer(string="Cajas", default = 0)
	sub_unidad = fields.Integer(string="Unidades", default = 0)
	no_charge_cost = fields.Boolean(string="¿Es producto sin cargo?", default=False)
	ubication_id = fields.Many2one('stock.position',string="Ubicación", default=False)
	sub_ubication_id = fields.Many2one('stock.subposition',string="Sub-ubicación", default=False)
	cantidad = fields.Float(string="Cantidad", related='qty_done')
	stock_product_ids = fields.Many2many('product.product', compute="_compute_products_stock")


	@api.constrains('lot_id', 'product_id')
	def _check_lot_product(self):
		for line in self:
			if line.lot_id and line.product_id != line.lot_id.sudo().product_id:
				#Modificación
				return
				#raise ValidationError(_(
				#	'This lot %(lot_name)s is incompatible with this product %(product_name)s',
				#	lot_name=line.lot_id.name,
				#	product_name=line.product_id.display_name
				#	))

	
	@api.onchange('product_id', 'product_uom_id','location_id')
	def _onchange_product_id(self):
		if self.product_id:
			self._compute_stock_available_ba()
			for move in self.picking_id.move_ids_without_package:
				if move.product_id == self.product_id:
					self.qty_unidad = move.unidad
					self.qty_sub_unidad = move.sub_unidad
					cantidad_requerida = move.product_uom_qty
					cantidad_reservada = 0
					for move_line in self.picking_id.move_line_ids_without_package:
						if move_line.product_id == self.product_id:
							cantidad_reservada = cantidad_reservada + move_line.product_uom_qty
					if cantidad_requerida == cantidad_reservada and self.picking_id.picking_type_id.code == 'outgoing':
						raise ValidationError('Para el producto '+ str(self.product_id.name) + ' ya se tiene cantidad reservada completa. Primero tiene que quitar la reserva actual para poder hacer modificaciones manuales.')

			if not self.id and self.user_has_groups('stock.group_stock_multi_locations'):
				self.location_dest_id = self.location_dest_id._get_putaway_strategy(self.product_id) or self.location_dest_id
			if self.picking_id:
				product = self.product_id.with_context(lang=self.picking_id.partner_id.lang or self.env.user.lang)
				self.description_picking = product._get_description(self.picking_id.picking_type_id)
			self.lots_visible = self.product_id.tracking != 'none'
			if not self.product_uom_id or self.product_uom_id.category_id != self.product_id.uom_id.category_id:
				if self.move_id.product_uom:
					self.product_uom_id = self.move_id.product_uom.id
				else:
					self.product_uom_id = self.product_id.uom_id.id


	@api.onchange('stock_quant_id')
	def onchange_stock_quant_id(self):
		move = []
		#print("Ingresa a onchange")
		if self.stock_quant_id != False:
			
			contador = 1
			registros = len(self.picking_id.move_line_ids_without_package)
			for move_line in self.picking_id.move_line_ids_without_package:
				if contador == registros:
					continue
				#print ("Esto es move_line.stock_quant_id",move_line.stock_quant_id)
				#print ("Esto es move arriba",move)
				#print ("Esto es contador",contador)
				if move_line.stock_quant_id in move and move_line.picking_id.picking_type_id.code == 'outgoing':
					raise ValidationError('El movimiento de Kardex ' + str(move_line.stock_quant_id.get_name()) + ' ya se encuentra relacionado en otra partida de las operaciones detalladas.')
				else:
					move.append(move_line.stock_quant_id)
				#print ("Esto es move abajo",move)
				contador = contador + 1



		if self.stock_quant_id != False:
			self.lot_id = self.stock_quant_id.lot_id.id

		if self.stock_quant_id != False and self.picking_id.picking_type_id.code == 'outgoing':
			self.ubication_id = self.stock_quant_id.ubication_id.id
			self.sub_ubication_id = self.stock_quant_id.sub_ubication_id.id


	@api.onchange('ubication_id')
	def onchange_ubication(self):
		if self.picking_id.picking_type_id.code != 'outgoing':
			self.sub_ubication_id = False

	@api.onchange('unidad','sub_unidad')
	def onchange_unidad_sub_unidad(self):
		for move in self:
			if move.sub_unidad < 0 or move.unidad < 0:
				move.unidad = 0
				move.sub_unidad = 0
				raise ValidationError('No puedes dar salida a una cantidad negativa.')
			if move.unidad >= 0:
				move.qty_done = (move.unidad * move.product_id.quantity_uom) + move.sub_unidad
			if move.sub_unidad >= 0:
				if move.product_id:
					if move.sub_unidad >= move.product_id.quantity_uom:
						piezas_empaques = int(move.sub_unidad/move.product_id.quantity_uom)
						move.unidad = move.unidad + int(move.sub_unidad/move.product_id.quantity_uom)
						move.sub_unidad = move.sub_unidad - (piezas_empaques *  move.product_id.quantity_uom)

				move.qty_done = (move.unidad * move.product_id.quantity_uom) + move.sub_unidad
			if move.sub_unidad < 0 or move.unidad < 0:
				raise ValidationError('No puedes dar salida a una cantidad negativa.')
			if move.stock_quant_id and move.picking_id.picking_type_id.code == 'outgoing':
				disponible = move.stock_quant_id.quantity - move.stock_quant_id.reserved_quantity
				if move.qty_done > disponible and move.product_uom_qty == 0:
					move.unidad = int(disponible/move.product_id.quantity_uom)
					move.sub_unidad = disponible - (move.unidad * move.product_id.quantity_uom)
					move.qty_done = disponible
					self.env.user.notify_danger(message='Se ingresó una cantidad mayor a la disponible en el movimiento kardex ' + str(move.stock_quant_id.get_name()) + ' la cantidad máxima disponible es de: ' + str(move.unidad) + ' Cajas y ' + str(move.sub_unidad) + ' Unidades.')

			if move.stock_quant_id and move.product_uom_qty > 0 and move.picking_id.picking_type_id.code == 'outgoing':
				total  = move.product_uom_qty + disponible
				if move.qty_done > total:
					move.unidad = int(total/move.product_id.quantity_uom)
					move.sub_unidad = total - (move.unidad * move.product_id.quantity_uom)
					move.qty_done = total
					self.env.user.notify_danger(message='Se ingresó una cantidad mayor a la disponible en el movimiento kardex ' + str(move.stock_quant_id.get_name()) + ' la cantidad máxima disponible es de: ' + str(move.unidad) + ' Cajas y ' + str(move.sub_unidad) + ' Unidades y puede que ya se encuentre una parte reservada.')
			if move.stock_quant_id:
				cantidad_total = 0
				if len(move.picking_id.move_line_ids_without_package) == 1:
					#print ("Ingresa al if arriba")
					cantidad_total = move.qty_done
				elif len(move.picking_id.move_line_ids_without_package) == 2:
					#print ("Ingresa a Elif")
					contador = 1
					for move_line_new in move.picking_id.move_line_ids_without_package:
						if contador == 2:
							cantidad_total = cantidad_total + move_line_new.qty_done
						contador = contador + 1
				elif len(move.picking_id.move_line_ids_without_package) > 2:
					#print ("Ingresa al tercer elif")
					contador = 1
					registros = len(move.picking_id.move_line_ids_without_package)
					registros_menos_uno = registros - 1 
					for move_line_new in move.picking_id.move_line_ids_without_package:
						#print ("Esto es cantidad en tercer elif",move_line_new.qty_done)
						#print ("Esto es move_line_new.id",move_line_new.id)
						if contador != registros_menos_uno:
							cantidad_total = cantidad_total + move_line_new.qty_done
							
						contador = contador + 1

				#print ("Esto es cantidad_total",cantidad_total)
				for move_id in move.picking_id.move_ids_without_package:
					if move_id.product_id.id == move.product_id.id:
						cantidad_move_id = move_id.product_uom_qty
						quantity_unit = move_id.unidad
						cantidad_sub_unidad = move_id.sub_unidad

				#print ("Esto es cantidad_move_id",cantidad_move_id)

				if cantidad_total > cantidad_move_id:
					self.env.user.notify_danger(message='Se ingresó una cantidad mayor a la requerida para el producto ' + str(move.product_id.name) + ' la cantidad requerida es de: ' + str(quantity_unit) + ' Cajas y ' + str(cantidad_sub_unidad) + ' Unidades y puede que ya se encuentre una parte agregada en otra partida, si no es así intente nuevamente.')
					if len(move.picking_id.move_line_ids_without_package) <= 2:
						move.unidad = int(cantidad_move_id/move.product_id.quantity_uom)
						move.sub_unidad = cantidad_move_id - (move.unidad * move.product_id.quantity_uom)
						move.qty_done = cantidad_move_id
					

					if len(move.picking_id.move_line_ids_without_package) > 2:
						contador = 2
						registros = len(move.picking_id.move_line_ids_without_package)
						cantidad_total_otros = 0 
						for move_line_new in move.picking_id.move_line_ids_without_package:
							if contador < registros:
								#print ("Esto es move_line_new.id",move_line_new.id)
								#print ("Esto es move.id",move.id)
								#print ("Esto es move_line_new.qty_done",move_line_new.qty_done)
								cantidad_total_otros = cantidad_total_otros + move_line_new.qty_done

							contador = contador + 1
						#print ("cantidad_total_otros abajo",cantidad_total_otros)
						cantidad_libre = cantidad_move_id - cantidad_total_otros
						if cantidad_libre == 0:
							move.unidad = 0
							move.sub_unidad = 0
							move.qty_done = 0
						else:
							move.unidad = int(cantidad_libre/move.product_id.quantity_uom)
							move.sub_unidad = cantidad_libre - (move.unidad * move.product_id.quantity_uom)
							move.qty_done = cantidad_libre



				


	@api.depends('product_id', 'product_uom_id', 'product_uom_qty')
	def _compute_product_qty(self):
		#print ("Ingresa a _compute_product_qty")
		for line in self:
			#print ("Esto es line.picking_id",line.picking_id)
			line._compute_products_stock()
			if line.product_id:
				line._compute_stock_available_ba()
			if line.stock_quant_id and line.picking_id.picking_type_id.code == 'outgoing':
				line.ubication_id = line.stock_quant_id.ubication_id.id
				line.sub_ubication_id = line.stock_quant_id.sub_ubication_id.id
			line.product_qty = line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id, rounding_method='HALF-UP')
			if line.product_uom_qty == 0:
				line.qty_unidad = 0
			else:
				line.qty_unidad = int(line.product_uom_qty / line.product_id.quantity_uom)
			line.qty_sub_unidad = line.product_uom_qty - (line.qty_unidad *  line.product_id.quantity_uom)

	
	@api.onchange('lot_name', 'lot_id')
	def _onchange_serial_number(self):
		res = {}
		##print ("Entra onchange of lot_id")
		if self.product_id.tracking == 'serial':
			if not self.qty_done:
				self.qty_done = 1

			message = None
			if self.lot_name or self.lot_id:
				move_lines_to_check = self._get_similar_move_lines() - self
				if self.lot_name:
					counter = Counter([line.lot_name for line in move_lines_to_check])
					if counter.get(self.lot_name) and counter[self.lot_name] > 1:
						message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
					elif not self.lot_id:
						counter = self.env['stock.production.lot'].search_count([
							('company_id', '=', self.company_id.id),
							('product_id', '=', self.product_id.id),
							('name', '=', self.lot_name),
							])
						if counter > 0:
							message = _('Existing Serial number (%s). Please correct the serial number encoded.') % self.lot_name
				elif self.lot_id:
					counter = Counter([line.lot_id.id for line in move_lines_to_check])
					if counter.get(self.lot_id.id) and counter[self.lot_id.id] > 1:
						message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
			if message:
				res['warning'] = {'title': _('Warning'), 'message': message}
		return res


	#def write(self, vals):
	#	#print ("Pasa en write")
	#	if self.env.context.get('bypass_reservation_update'):
	#		return super(StockMoveLine, self).write(vals)
	#	if 'product_id' in vals and any(vals.get('state', ml.state) != 'draft' and vals['product_id'] != ml.product_id.id for ml in self):
	#		raise UserError(_("Changing the product is only allowed in 'Draft' state."))

	#	moves_to_recompute_state = self.env['stock.move']
	#	Quant = self.env['stock.quant']
	#	precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
	#	triggers = [
	#	    ('location_id', 'stock.location'),
	#	    ('location_dest_id', 'stock.location'),
	#	    ('lot_id', 'stock.production.lot'),
	#	    ('package_id', 'stock.quant.package'),
	#	    ('result_package_id', 'stock.quant.package'),
	#	    ('owner_id', 'res.partner')
	#	]
	#	updates = {}
	#	for key, model in triggers:
	#		if key in vals:
	#			updates[key] = self.env[model].browse(vals[key])

	#	if 'result_package_id' in updates:
	#		for ml in self.filtered(lambda ml: ml.package_level_id):
	#			if updates.get('result_package_id'):
	#				ml.package_level_id.package_id = updates.get('result_package_id')
	#			else:
	#				package_level = ml.package_level_id
	#				ml.package_level_id = False
	#				package_level.unlink()

	#	if updates or 'product_uom_qty' in vals:
	#		for ml in self.filtered(lambda ml: ml.state in ['partially_available', 'assigned'] and ml.product_id.type == 'product'):
	#			if 'product_uom_qty' in vals:
	#				new_product_uom_qty = ml.product_uom_id._compute_quantity(
	#					vals['product_uom_qty'], ml.product_id.uom_id, rounding_method='HALF-UP')
	#				if float_compare(new_product_uom_qty, 0, precision_rounding=ml.product_id.uom_id.rounding) < 0:
	#					raise UserError(_('Reserving a negative quantity is not allowed.'))
	#			else:
	#				new_product_uom_qty = ml.product_qty

	#			if not ml._should_bypass_reservation(ml.location_id):
	#				Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True, move_type= ml.picking_id.picking_type_id.code, stock_quant_id = ml.stock_quant_id)

	#			if not ml._should_bypass_reservation(updates.get('location_id', ml.location_id)):
	#				reserved_qty = 0
	#				try:
	#					q = Quant._update_reserved_quantity(ml.product_id, updates.get('location_id', ml.location_id), new_product_uom_qty, lot_id=updates.get('lot_id', ml.lot_id),
	#						package_id=updates.get('package_id', ml.package_id), owner_id=updates.get('owner_id', ml.owner_id), strict=True, move_type= ml.picking_id.picking_type_id.code, stock_quant_id = ml.stock_quant_id)
	#					reserved_qty = sum([x[1] for x in q])
	#				except UserError:
	#					pass
	#				if reserved_qty != new_product_uom_qty:
	#					new_product_uom_qty = ml.product_id.uom_id._compute_quantity(reserved_qty, ml.product_uom_id, rounding_method='HALF-UP')
	#					moves_to_recompute_state |= ml.move_id
	#					ml.with_context(bypass_reservation_update=True).product_uom_qty = new_product_uom_qty


	#	if updates or 'qty_done' in vals:
	#		next_moves = self.env['stock.move']
	#		mls = self.filtered(lambda ml: ml.move_id.state == 'done' and ml.product_id.type == 'product')
	#		if not updates:  # we can skip those where qty_done is already good up to UoM rounding
	#			mls = mls.filtered(lambda ml: not float_is_zero(ml.qty_done - vals['qty_done'], precision_rounding=ml.product_uom_id.rounding))
	#		for ml in mls:
	#			# undo the original move line
	#			qty_done_orig = ml.move_id.product_uom._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
	#			in_date = Quant._update_available_quantity(ml.product_id, ml.location_dest_id, -qty_done_orig, lot_id=ml.lot_id,
	#				package_id=ml.result_package_id, owner_id=ml.owner_id)[1]
	#			Quant._update_available_quantity(ml.product_id, ml.location_id, qty_done_orig, lot_id=ml.lot_id,
	#				package_id=ml.package_id, owner_id=ml.owner_id, in_date=in_date)

				# move what's been actually done
	#			product_id = ml.product_id
	#			location_id = updates.get('location_id', ml.location_id)
	#			location_dest_id = updates.get('location_dest_id', ml.location_dest_id)
	#			qty_done = vals.get('qty_done', ml.qty_done)
	#			lot_id = updates.get('lot_id', ml.lot_id)
	#			package_id = updates.get('package_id', ml.package_id)
	#			result_package_id = updates.get('result_package_id', ml.result_package_id)
	#			owner_id = updates.get('owner_id', ml.owner_id)
	#			quantity = ml.move_id.product_uom._compute_quantity(qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
	#			if not ml._should_bypass_reservation(location_id):
	#				ml._free_reservation(product_id, location_id, quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
	#			if not float_is_zero(quantity, precision_digits=precision):
	#				available_qty, in_date = Quant._update_available_quantity(product_id, location_id, -quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
	#				if available_qty < 0 and lot_id:
						# see if we can compensate the negative quants with some untracked quants
	#					untracked_qty = Quant._get_available_quantity(product_id, location_id, lot_id=False, package_id=package_id, owner_id=owner_id, strict=True)
	#					if untracked_qty:
	#						taken_from_untracked_qty = min(untracked_qty, abs(available_qty))
	#						Quant._update_available_quantity(product_id, location_id, -taken_from_untracked_qty, lot_id=False, package_id=package_id, owner_id=owner_id)
	#						Quant._update_available_quantity(product_id, location_id, taken_from_untracked_qty, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
	#						if not ml._should_bypass_reservation(location_id):
	#							ml._free_reservation(ml.product_id, location_id, untracked_qty, lot_id=False, package_id=package_id, owner_id=owner_id)
	#				Quant._update_available_quantity(product_id, location_dest_id, quantity, lot_id=lot_id, package_id=result_package_id, owner_id=owner_id, in_date=in_date)

				# Unreserve and reserve following move in order to have the real reserved quantity on move_line.
	#			next_moves |= ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))

				# Log a note
	#			if ml.picking_id:
	#				ml._log_message(ml.picking_id, ml, 'stock.track_move_template', vals)

	#	res = super(StockMoveLine, self).write(vals)

		# Update scrap object linked to move_lines to the new quantity.
	#	if 'qty_done' in vals:
	#		for move in self.mapped('move_id'):
	#			if move.scrapped:
	#				move.scrap_ids.write({'scrap_qty': move.quantity_done})

	#	if updates or 'qty_done' in vals:
	#		moves = self.filtered(lambda ml: ml.move_id.state == 'done').mapped('move_id')
	#		moves |= self.filtered(lambda ml: ml.move_id.state not in ('done', 'cancel') and ml.move_id.picking_id.immediate_transfer and not ml.product_uom_qty).mapped('move_id')
	#		for move in moves:
	#			move.product_uom_qty = move.quantity_done
	#		next_moves._do_unreserve()
	#		next_moves._action_assign()

	#	if moves_to_recompute_state:
	#		moves_to_recompute_state._recompute_state()

	#	return res



	def _action_done(self):
		#print ("Pasa en _action_done")
		Quant = self.env['stock.quant']
		ml_ids_tracked_without_lot = OrderedSet()
		ml_ids_to_delete = OrderedSet()
		ml_ids_to_create_lot = OrderedSet()
		
		for ml in self:
			
			# Check here if `ml.qty_done` respects the rounding of `ml.product_uom_id`.
			uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
			precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
			qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')
			if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
				raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision \
				defined on the unit of measure "%s". Please change the quantity done or the \
				rounding precision of your unit of measure.') % (ml.product_id.display_name, ml.product_uom_id.name))

			qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
			if qty_done_float_compared > 0:
				if ml.product_id.tracking != 'none':
					picking_type_id = ml.move_id.picking_type_id
					if picking_type_id:
						if picking_type_id.use_create_lots:
							# If a picking type is linked, we may have to create a production lot on
							# the fly before assigning it to the move line if the user checked both
							# `use_create_lots` and `use_existing_lots`.
							if ml.lot_name:
								if ml.product_id.tracking == 'lot' and not ml.lot_id:
									lot = self.env['stock.production.lot'].search([
										('company_id', '=', ml.company_id.id),
										('product_id', '=', ml.product_id.id),
										('name', '=', ml.lot_name),
									], limit=1)
									if lot:
										ml.lot_id = lot.id
									else:
										ml_ids_to_create_lot.add(ml.id)
								else:
									ml_ids_to_create_lot.add(ml.id)
						elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
							# If the user disabled both `use_create_lots` and `use_existing_lots`
							# checkboxes on the picking type, he's allowed to enter tracked
							# products without a `lot_id`.
							continue
					elif ml.move_id.inventory_id:
						# If an inventory adjustment is linked, the user is allowed to enter
						# tracked products without a `lot_id`.
						continue

					if not ml.lot_id and ml.id not in ml_ids_to_create_lot:
						ml_ids_tracked_without_lot.add(ml.id)
			elif qty_done_float_compared < 0:
				raise UserError(_('No negative quantities allowed'))
			else:
				ml_ids_to_delete.add(ml.id)

		if ml_ids_tracked_without_lot:
		    mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
		    raise UserError(_('You need to supply a Lot/Serial Number for product: \n - ') +
		                      '\n - '.join(mls_tracked_without_lot.mapped('product_id.display_name')))
		ml_to_create_lot = self.env['stock.move.line'].browse(ml_ids_to_create_lot)

		ml_to_create_lot._create_and_assign_production_lot()

		mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
		mls_to_delete.unlink()

		mls_todo = (self - mls_to_delete)
		mls_todo._check_company()

		# Now, we can actually move the quant.
		ml_ids_to_ignore = OrderedSet()
		for ml in mls_todo:
			#print ("Esto es ml",ml)
			#print ("Esto es ml",ml.lot_id)
			#print ("Esto es ml.move_id.sale_line_id",ml.move_id.sale_line_id.id)
			move_type = ml.picking_id.picking_type_id.code


			if ml.product_id.type == 'product':
				rounding = ml.product_uom_id.rounding

		    # if this move line is force assigned, unreserve elsewhere if needed
			if not ml._should_bypass_reservation(ml.location_id) and float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=rounding) > 0:
				#print("Ingresa 1")
				qty_done_product_uom = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id, rounding_method='HALF-UP')
				extra_qty = qty_done_product_uom - ml.product_qty
				ml_to_ignore = self.env['stock.move.line'].browse(ml_ids_to_ignore)
				ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, ml_to_ignore=ml_to_ignore)
			# unreserve what's been reserved
			if not ml._should_bypass_reservation(ml.location_id) and ml.product_id.type == 'product' and ml.product_qty:
				#print("Ingresa 2")
				Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

			# move what's been actually done
			quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
			available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, no_charge_cost=ml.no_charge_cost, move_type=move_type, stock_quant_id=ml.stock_quant_id, ubication_id=ml.ubication_id, sub_ubication_id=ml.sub_ubication_id)
			if available_qty < 0 and ml.lot_id:
				#print("Ingresa 3")
				# see if we can compensate the negative quants with some untracked quants
				untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
				if untracked_qty:
					#print("Ingresa 4")
					taken_from_untracked_qty = min(untracked_qty, abs(quantity))
					Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, no_charge_cost=ml.no_charge_cost, move_type=move_type, stock_quant_id=ml.stock_quant_id, ubication_id=ml.ubication_id, sub_ubication_id=ml.sub_ubication_id)
					Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, no_charge_cost=ml.no_charge_cost, move_type=move_type, stock_quant_id=ml.stock_quant_id, ubication_id=ml.ubication_id, sub_ubication_id=ml.sub_ubication_id)
			Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date, no_charge_cost=ml.no_charge_cost, move_type=move_type, stock_quant_id=ml.stock_quant_id, ubication_id=ml.ubication_id, sub_ubication_id=ml.sub_ubication_id)
			ml_ids_to_ignore.add(ml.id)
		# Reset the reserved quantity as we just moved it to the destination location.
		mls_todo.with_context(bypass_reservation_update=True).write({
			'product_uom_qty': 0.00,
			'date': fields.Datetime.now(),
		})


	def _create_and_assign_production_lot(self):
		#Modificación para que solo se creé un numero de lote en caso de existir 2 partidas o mas en stokc.move.line con el mismo lote.
		lotes = []
		lotes_creados = []
		for ml in self:
			if ml.lot_name not in lotes:
				lot_vals = {
					'company_id': ml.move_id.company_id.id,
					'name': ml.lot_name,
					'product_id': ml.product_id.id,
				}
				lots = self.env['stock.production.lot'].create(lot_vals)
				lotes.append(ml.lot_name)
				lotes_creados.append(lots)
				ml.lot_id = lots.id
			else:
				lote = self.env['stock.production.lot'].search([('name', '=',ml.lot_name),('product_id', '=',ml.product_id.id),('company_id', '=', ml.move_id.company_id.id)])
				
				if not lote:
					for lote_anterior in lotes_creados:
						if ml.lot_name == lote_anterior.name:
							ml.lot_id = lote_anterior.id

				else:
					ml.lot_id = lote.id
	#@api.model
	#def unlink(self):
	#	precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
	#	for ml in self:
	#		if ml.state in ('done', 'cancel'):
	#			raise UserError(_('You can not delete product moves if the picking is done. You can only correct the done quantities.'))
	#		if ml.product_id.type == 'product' and not ml._should_bypass_reservation(ml.location_id) and not float_is_zero(ml.product_qty, precision_digits=precision):
	#			#print ("Ingresa a donde deberia quitar reserva")
	#			self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True, move_type= ml.picking_id.picking_type_id.code, stock_quant_id = ml.stock_quant_id)
	#	moves = self.mapped('move_id')
	#	res = super(StockMoveLine, self).unlink()
	#	if moves:
	#		moves.with_prefetch()._recompute_state()
	#	return res