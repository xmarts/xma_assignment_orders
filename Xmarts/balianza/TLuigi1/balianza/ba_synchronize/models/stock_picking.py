# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

#Modificaciones en pedidos para gestión de reserva manual de producto.

class Picking(models.Model):

	_inherit='stock.picking'

	

	purchase_id = fields.Many2one('purchase.order', related='move_lines.purchase_line_id.order_id',
        string="Purchase Orders", readonly=True, store=True)
	x_css = fields.Html(string='CSS',sanitize=False,compute='_compute_css',store=False)

	trans_interna = fields.Boolean(string="Es una transferencia interna?", readonly=True, related='move_lines.trans_interna', store=True)


	def reserved_quantity_manually(self):
		#print ("Ingresa a reservar cantidades manualmente")
		bandera=False
		for move_line in self.move_line_ids_without_package:
			#print ("Ingresa a move_line un reserved_quantity_manually",move_line)
			disponible = move_line.stock_quant_id.quantity - move_line.stock_quant_id.reserved_quantity
			if move_line.qty_done > 0  and move_line.product_uom_qty == 0 and self.state != 'assigned':
				#print("Ingresa a if1")
				if move_line.qty_done > disponible:
					move_line.unidad = int(disponible/move_line.product_id.quantity_uom)
					move_line.sub_unidad = disponible - (move_line.unidad * move_line.product_id.quantity_uom)
					move_line.qty_done = disponible
					self.env.user.notify_danger(message='Se actualizó la cantidad ingresada en el movimiento ' + str(move_line.stock_quant_id.get_name()) + ' la cantidad máxima disponible para reserva es de: ' + str(move_line.unidad) + ' Cajas y ' + str(move_line.sub_unidad) + ' Unidades por lo que solo ésta cantidad fué reservada, verifique otros movimientos que pudieran estar afectando.')
				move_line.product_uom_qty = move_line.qty_done
				quant = self.env['stock.quant'].search([('id','=',move_line.stock_quant_id.id)])
				quant.reserved_quantity = quant.reserved_quantity + move_line.product_uom_qty
				move_line.state = 'assigned'
				bandera = True
			if move_line.qty_done > 0  and move_line.product_uom_qty == 0 and self.state == 'assigned':
				#print("Ingresa a if1")
				if move_line.qty_done > disponible:
					move_line.unidad = int(disponible/move_line.product_id.quantity_uom)
					move_line.sub_unidad = disponible - (move_line.unidad * move_line.product_id.quantity_uom)
					move_line.qty_done = disponible
					self.env.user.notify_danger(message='Se actualizó la cantidad ingresada en el movimiento ' + str(move_line.stock_quant_id.get_name()) + ' la cantidad máxima disponible para reserva es de: ' + str(move_line.unidad) + ' Cajas y ' + str(move_line.sub_unidad) + ' Unidades por lo que solo ésta cantidad fué reservada, verifique otros movimientos que pudieran estar afectando.')
				move_line.product_uom_qty = move_line.qty_done
				move_line.state = 'assigned'
			if move_line.qty_done < move_line.product_uom_qty and move_line.product_uom_qty != 0:
				#print("Ingresa a if2")
				move_line.product_uom_qty = move_line.qty_done

			if move_line.qty_done > move_line.product_uom_qty and move_line.product_uom_qty != 0:
				#print("Ingresa a if3")
				total  = move_line.product_uom_qty + disponible
				if move_line.qty_done > total:
					move_line.unidad = int(total/move_line.product_id.quantity_uom)
					move_line.sub_unidad = total - (move_line.unidad * move_line.product_id.quantity_uom)
					move_line.qty_done = total
					self.env.user.notify_danger(message='Se actualizó la cantidad ingresada en el movimiento ' + str(move_line.stock_quant_id.get_name()) + ' la cantidad máxima disponible para reserva es de: ' + str(move_line.unidad) + ' Cajas y ' + str(move_line.sub_unidad) + ' Unidades por lo que solo ésta cantidad fué reservada, verifique otros movimientos que pudieran estar afectando.')

				move_line.product_uom_qty = move_line.qty_done




		if bandera == True and self.state != 'assigned':
			self.state = 'assigned'

		for move in self.move_ids_without_package:
			if move.quantity_done != 0:
				move.state = 'assigned'

	@api.depends('move_type', 'immediate_transfer', 'move_lines.state', 'move_lines.picking_id')
	def _compute_state(self):
		for picking in self:
			if not picking.move_lines:
				picking.state = 'draft'
			elif any(move.state == 'draft' for move in picking.move_lines):
				picking.state = 'draft'
			elif all(move.state == 'cancel' for move in picking.move_lines):
				picking.state = 'cancel'
			elif all(move.state in ['cancel', 'done'] for move in picking.move_lines):
				picking.state = 'done'
			else:
				relevant_move_state = picking.move_lines._get_relevant_state_among_moves()
				if picking.immediate_transfer and relevant_move_state not in ('draft', 'cancel', 'done'):
					picking.state = 'assigned'
				elif relevant_move_state == 'partially_available':
					picking.state = 'assigned'
				else:
					picking.state = relevant_move_state
			if picking.move_ids_without_package:
				for move in picking.move_ids_without_package:
					move._compute_reserved_availability()


	def write(self, vals):
		res = super(Picking, self).write(vals)
		#print ("Ingresa a write esto es self",self)
		#if self.id:
			##print ("Esto es self.state",self.state)
			#if self.state == 'confirmed':
				#self.action_assign()
		return res

	def action_assign(self):
		self.do_unreserve()
		self.filtered(lambda picking: picking.state == 'draft').action_confirm()
		moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
		if not moves:
			raise UserError(_('Nothing to check the availability for.'))
		package_level_done = self.mapped('package_level_ids').filtered(lambda pl: pl.is_done and pl.state == 'confirmed')
		package_level_done.write({'is_done': False})
		moves._action_assign()
		package_level_done.write({'is_done': True})

		return True

	@api.depends('state')
	def _compute_css(self):
		for application in self:
			if application.state == 'waiting':
				application.x_css = '<style>.o_form_button_edit {display: none !important;}</style>'
			else:
				application.x_css = False

	def _pre_action_done_hook(self):
		#print ("_pre_action_done_hook",self.move_line_ids_without_package)
		for move_linee in self.move_line_ids_without_package:
			#print ("Esto es move_linee.ubication_id",move_linee.ubication_id)
			#print ("Esto es move_linee.sub_ubication_id",move_linee.sub_ubication_id)
			#print ("Esto es self.picking_type_id.code",self.picking_type_id.code)
			if not move_linee.ubication_id and self.picking_type_id.code == 'internal' or not move_linee.sub_ubication_id and self.picking_type_id.code == 'internal':
				raise ValidationError('Para el producto: '+ str(move_linee.product_id.name) +' no se ah ingresado la ubicación o sub_ubicación.')
		for move in self.move_ids_without_package:
			if move.quantity_done > move.product_uom_qty:
				raise ValidationError('Para el producto: '+ str(move.product_id.name) +' no se puede ingresar una cantidad mayor a las unidades requeridas del pedido.')
			if self.purchase_id:
				unidades_sc = (move.unidad_sc * move.product_id.quantity_uom) + move.sub_unidad_sc
				sum_qty = 0
				sum_qty_sc = 0
				for move_line in move.move_line_ids:
					if move_line.no_charge_cost == True:
						sum_qty_sc = sum_qty_sc + move_line.qty_done
					else:
						sum_qty = sum_qty + move_line.qty_done
				max_qty = move.product_uom_qty - unidades_sc

				if move.unidad_sc !=0 or move.sub_unidad_sc !=0:
					if move.quantity_done == move.product_uom_qty and sum_qty_sc == 0 and move.picking_id.picking_type_id.code == 'incoming':
						raise ValidationError('Para el producto: '+ str(move.product_id.name) +' está ingresando la cantidad total de la orden de compra sin señalar las cantidades sin cargo.')
				if move.unidad !=0 or move.sub_unidad !=0:
					if move.quantity_done == move.product_uom_qty and sum_qty == 0 and move.picking_id.picking_type_id.code == 'incoming':
						raise ValidationError('Para el producto: '+ str(move.product_id.name) +' está ingresando la cantidad total de la orden de compra sin señalar las cantidades con cargo.')
				if sum_qty > max_qty and move.picking_id.picking_type_id.code == 'incoming':
					raise ValidationError('Para el producto: '+ str(move.product_id.name) +' está ingresando una cantidad mayor a las unidades requeridas del pedido con cargo.')
				if sum_qty_sc > unidades_sc and move.picking_id.picking_type_id.code == 'incoming':
					raise ValidationError('Para el producto: '+ str(move.product_id.name) +' está ingresando una cantidad mayor a las unidades requeridas del pedido sin cargo.')
		if not self.env.context.get('skip_immediate'):
			pickings_to_immediate = self._check_immediate()
			if pickings_to_immediate:
				return pickings_to_immediate._action_generate_immediate_wizard(show_transfers=self._should_show_transfers())

		if not self.env.context.get('skip_backorder'):
			pickings_to_backorder = self._check_backorder()
			if pickings_to_backorder:
				return pickings_to_backorder._action_generate_backorder_wizard(show_transfers=self._should_show_transfers())
		return True
