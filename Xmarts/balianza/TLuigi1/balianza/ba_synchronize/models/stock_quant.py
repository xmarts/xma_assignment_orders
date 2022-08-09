# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.osv import expression
import logging
from psycopg2 import Error, OperationalError

#Modificaciones para adecuación con Kardex SIA, se realizaron multiples modificaciones afectando funcionalidad base en la cual no se tenia un control de lote exacto de salida de producto.

class StockQuant(models.Model):

	_inherit='stock.quant'

	def name_get(self):

		res = []

		for rec in self:
			res.append((rec.id,'Lote:%s, Cantidad libre: %s Unidades, Ubicación: %s,%s' % (rec.lot_id.name, rec.quantity - rec.reserved_quantity, rec.ubication_id.name, rec.sub_ubication_id.name)))
		return res

	def get_name(self):

		name = 'Lote:' +str(self.lot_id.name)+', Cantidad libre: '+ str(self.quantity - self.reserved_quantity)+ ' Unidades, Ubicación: ' + str(self.ubication_id.name) +', '+ str(self.sub_ubication_id.name)
		return name
		

	packaging_content = fields.Integer(string="Contenido por empaque", readonly=True)
	packing_quantity = fields.Integer(string="Cantidad empaque", readonly=True)
	packing_unit_id = fields.Many2one('uom.uom', string="Unidad empaque", readonly=True)
	quantity_unit = fields.Integer(string="Cantidad unidad", readonly=True)
	unit_id = fields.Many2one('uom.uom', string="Unidad", readonly=True)
	no_charge_cost = fields.Boolean(string="¿Es producto sin cargo?", default=False, readonly=True)
	ubication_id = fields.Many2one('stock.position',string="Ubicación", default=False)
	sub_ubication_id = fields.Many2one('stock.subposition',string="Sub-ubicación", default=False)

	@api.model
	def create(self, vals):
		res = super(StockQuant, self).create(vals)
		res.packing_quantity = res.quantity / res.product_id.quantity_uom
		res.packing_unit_id = res.product_id.sub_type_uom.id
		res.packaging_content = res.product_id.quantity_uom
		res.unit_id = res.product_id.uom_id.id
		if res.quantity > 0:
			if res.packing_quantity > 0:
				res.quantity_unit = res.quantity - (res.packing_quantity *  res.product_id.quantity_uom)
			else:
				res.quantity_unit = res.quantity
		else:
			if res.packing_quantity < 0:
				res.quantity_unit = res.quantity - (res.packing_quantity *  res.product_id.quantity_uom)
			else:
				res.quantity_unit = res.quantity

		return res



	@api.constrains('quantity')
	def check_quantity(self):
		for quant in self:
			#print ("Esto es quantity",quant.quantity)
			quant.packing_quantity = quant.quantity / quant.product_id.quantity_uom
			quant.packing_unit_id = quant.product_id.sub_type_uom.id
			quant.packaging_content = quant.product_id.quantity_uom
			quant.unit_id = quant.product_id.uom_id.id
			if quant.quantity > 0:
				if quant.packing_quantity > 0:
					quant.quantity_unit = quant.quantity - (quant.packing_quantity *  quant.product_id.quantity_uom)
				else:
					quant.quantity_unit = quant.quantity
			else:
				if quant.packing_quantity < 0:
					quant.quantity_unit = quant.quantity - (quant.packing_quantity *  quant.product_id.quantity_uom)
				else:
					quant.quantity_unit = quant.quantity
			if float_compare(quant.quantity, 1, precision_rounding=quant.product_uom_id.rounding) > 0 and quant.lot_id and quant.product_id.tracking == 'serial':
				raise ValidationError(_('The serial number has already been assigned: \n Product: %s, Serial Number: %s') % (quant.product_id.display_name, quant.lot_id.name))

	@api.model
	def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None, no_charge_cost=None,  move_type= None, stock_quant_id = None, ubication_id = None, sub_ubication_id = None):
		#print ("Esto es self",self)
		self = self.sudo()
		#print ("Esto es self abajo",self)

		#print ("Esto es self arriba context",self.env.context)
		quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
		if lot_id and quantity > 0:
			quants = quants.filtered(lambda q: q.lot_id)
		#print ("Esto es quants default",quants)
		#print ("Esto es stock_quant_id",stock_quant_id)
		#print ("Esto es quantity",quantity)
		#print ("Esto es move_type",move_type)
		if move_type != 'incoming' and stock_quant_id and quantity < 0:
			quants = self.env['stock.quant'].search([('id','=',stock_quant_id.id)])
		if move_type != 'outgoing' and stock_quant_id and quantity < 0:
			quants = self.env['stock.quant'].search([('id','=',stock_quant_id.id)])
			#print ("Esto es new quants", quants)
		incoming_dates = [d for d in quants.mapped('in_date') if d]
		incoming_dates = [fields.Datetime.from_string(incoming_date) for incoming_date in incoming_dates]
		if in_date:
			incoming_dates += [in_date]

		if incoming_dates:
			in_date = fields.Datetime.to_string(min(incoming_dates))
		else:
			in_date = fields.Datetime.now()

		#print ("Esto es move_type",move_type)
		#print ("Esto es stock_quant_id",stock_quant_id)


		if len(quants) >= 2 and  move_type == 'outgoing' and quantity<0:
			contador = 1
			quantity_remaining = abs(quantity)
			for quant in quants:

				#print("Esto es quant en if1",quant)
				#print("Esto es quantity_remaining1",quantity_remaining)

				if quant.quantity >= quantity_remaining and contador == 1:
					#print ("Ingresa al segundo IF quant.quantity3",quant.quantity)
					
					quant.write({
					'quantity': quant.quantity - quantity_remaining,
					'in_date': in_date,
					})
					quantity_remaining = 0
					contador = contador + 1

				elif quant.quantity < quantity_remaining and contador == 1:
					#print ("Ingresa al segundo IF quant.quantity4",quant.quantity)
					quantity_remaining = quantity_remaining-quant.quantity
					quant.write({
					'quantity': 0,
					'in_date': in_date,
					})
					contador = contador + 1

				

				elif quant.quantity >= quantity_remaining and quantity_remaining != 0 and contador != 1:
					#print ("Ingresa al segundo IF quant.quantity5",quant.quantity)
					quant.write({
					'quantity': quant.quantity - quantity_remaining,
					'in_date': in_date,
					})
					quantity_remaining = 0

				elif quant.quantity < quantity_remaining and quantity_remaining != 0 and contador != 1:
					#print ("Ingresa al segundo IF quant.quantity6",quant.quantity)
					quantity_remaining = quantity_remaining-quant.quantity
					quant.write({
					'quantity': 0,
					'in_date': in_date,
					})


			return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True), fields.Datetime.from_string(in_date)

		if len(quants) >= 2 and  move_type == 'internal' and quantity<0:
			contador = 1
			quantity_remaining = abs(quantity)
			for quant in quants:

				#print("Esto es quant en if1",quant)
				#print("Esto es quantity_remaining1",quantity_remaining)
				#print("Esto es location_id",location_id)
				#print("Esto es quant.location_id",quant.location_id)

				if location_id == quant.location_id and quant.quantity >= quantity_remaining and contador == 1:
					#print ("Ingresa al segundo IF quant.quantity3",quant.quantity)
					
					quant.write({
					'quantity': quant.quantity - quantity_remaining,
					'in_date': in_date,
					})
					quantity_remaining = 0
					contador = contador + 1

				elif location_id == quant.location_id and quant.quantity < quantity_remaining and contador == 1:
					#print ("Ingresa al segundo IF quant.quantity4",quant.quantity)
					quantity_remaining = quantity_remaining-quant.quantity
					quant.write({
					'quantity': 0,
					'in_date': in_date,
					})
					contador = contador + 1

				

				elif location_id == quant.location_id and quant.quantity >= quantity_remaining and quantity_remaining != 0 and contador != 1:
					#print ("Ingresa al segundo IF quant.quantity5",quant.quantity)
					quant.write({
					'quantity': quant.quantity - quantity_remaining,
					'in_date': in_date,
					})
					quantity_remaining = 0

				elif quant.quantity < quantity_remaining and quantity_remaining != 0 and contador != 1:
					#print ("Ingresa al segundo IF quant.quantity6",quant.quantity)
					quantity_remaining = quantity_remaining-quant.quantity
					quant.write({
					'quantity': 0,
					'in_date': in_date,
					})


			return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True), fields.Datetime.from_string(in_date)

				

		else:
			for quant in quants:
				#print("Esto es quant en else",quant)
				try:
					with self._cr.savepoint(flush=False):
						#print ("Esto es ubication_id",ubication_id)
						#print ("Esto es sub_ubication_id",sub_ubication_id)
						if stock_quant_id and not ubication_id and not sub_ubication_id:
							#print("Aqui si ingreso al IF que busco1",quantity)
							self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
							quant.write({
							'quantity': quant.quantity + quantity,
							'in_date': in_date,
							})
							break

						elif stock_quant_id and ubication_id and sub_ubication_id:
							if quantity < 0:
								#print("Aqui si ingreso al IF que busco1.1",quantity)
								self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
								quant.write({
								'quantity': quant.quantity + quantity,
								'in_date': in_date,
								})
								break
							if quantity > 0:
								#print("Aqui si ingreso al IF que busco1.2",quantity)

								if quant.no_charge_cost == False and no_charge_cost == False and quant.ubication_id.id == ubication_id.id and quant.sub_ubication_id.id == sub_ubication_id.id:
									#print("Aqui si ingreso al IF que busco2.1",quantity)
									self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
									quant.write({
									'quantity': quant.quantity + quantity,
									'in_date': in_date,
									})
									break
								elif quant.no_charge_cost == True and no_charge_cost == True and quant.ubication_id.id == ubication_id.id and quant.sub_ubication_id.id == sub_ubication_id.id:
									#print("Aqui si ingreso al IF que busco abajo2.1",quantity)
									self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
									quant.write({
									'quantity': quant.quantity + quantity,
									'in_date': in_date,
									})
									break
								else:
									stock_quant = self.create({
										'product_id': product_id.id,
										'location_id': location_id.id,
										'quantity': quantity,
										'lot_id': lot_id and lot_id.id,
										'package_id': package_id and package_id.id,
										'owner_id': owner_id and owner_id.id,
										'in_date': in_date,
										'no_charge_cost': no_charge_cost,
										'ubication_id': ubication_id.id,
										'sub_ubication_id': sub_ubication_id.id,
									})
									break

						elif quant.no_charge_cost == False and no_charge_cost == False and quant.ubication_id.id == ubication_id.id and quant.sub_ubication_id.id == sub_ubication_id.id:
							#print("Aqui si ingreso al IF que busco2",quantity)
							self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
							quant.write({
							'quantity': quant.quantity + quantity,
							'in_date': in_date,
							})
							break
						elif quant.no_charge_cost == True and no_charge_cost == True and quant.ubication_id.id == ubication_id.id and quant.sub_ubication_id.id == sub_ubication_id.id:
							#print("Aqui si ingreso al IF que busco abajo2",quantity)
							self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
							quant.write({
							'quantity': quant.quantity + quantity,
							'in_date': in_date,
							})
							break
				except OperationalError as e:
					if e.pgcode == '55P03':  # could not obtain the lock
						continue
					else:
						self.clear_caches()
						raise
			else:
				stock_quant = self.create({
					'product_id': product_id.id,
					'location_id': location_id.id,
					'quantity': quantity,
					'lot_id': lot_id and lot_id.id,
					'package_id': package_id and package_id.id,
					'owner_id': owner_id and owner_id.id,
					'in_date': in_date,
					'no_charge_cost': no_charge_cost,
					'ubication_id': ubication_id.id,
					'sub_ubication_id': sub_ubication_id.id,
				})
				#print (" ",stock_quant)

			return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True), fields.Datetime.from_string(in_date)

	@api.model
	def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False, move_type= None, stock_quant_id = None, sale_id = None):
		self = self.sudo()
		#print ("Esto es self",self)
		#print ("Esto es owner_id",owner_id)
		rounding = product_id.uom_id.rounding
		quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
		#print ("Esto es quants",quants)
		#print ("Esto es quantity",quantity)
		if sale_id and quants:
			#print ("Ingresa cuando es venta")
			parametros = self.env['params.serie.point.sale.warehouse'].search([('serie_id','=',sale_id.serie_id.id),('company_id','=',sale_id.company_id.id)])
			almacenes = []
			for warehouse in parametros.warehouse_ids:
				if warehouse.status == True:
					almacenes.append(warehouse.warehouse_id.id)

			#print ("Esto es almacenes",almacenes)
			new_quants = []
			for quant in quants:
				if quant.location_id.id in almacenes:
					new_quants.append(quant.id)
			#print ("Esto es quants ahora",new_quants)
			quants = self.env['stock.quant'].search([('id','in',new_quants)])
			#print ("Esto es quants abajo ahora",quants)
		if move_type != 'incoming' and stock_quant_id:
			quants = self.env['stock.quant'].search([('id','=',stock_quant_id.id)])
			#print ("Esto es new quants", quants)
		reserved_quants = []
		if float_compare(quantity, 0, precision_rounding=rounding) > 0:
			available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
			if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
				raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
		elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
			available_quantity = sum(quants.mapped('reserved_quantity'))
			if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
				raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
		else:
			return reserved_quants
		
		for quant in quants:
			if float_compare(quantity, 0, precision_rounding=rounding) > 0:
				max_quantity_on_quant = quant.quantity - quant.reserved_quantity
				if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
					continue
				max_quantity_on_quant = min(max_quantity_on_quant, quantity)
				quant.reserved_quantity += max_quantity_on_quant
				reserved_quants.append((quant, max_quantity_on_quant))
				quantity -= max_quantity_on_quant
				available_quantity -= max_quantity_on_quant
			else:
				max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
				quant.reserved_quantity -= max_quantity_on_quant
				reserved_quants.append((quant, -max_quantity_on_quant))
				quantity += max_quantity_on_quant
				available_quantity += max_quantity_on_quant

			if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
				break
		return reserved_quants

	@api.model
	def _get_removal_strategy(self, product_id, location_id):
		if product_id.categ_id.removal_strategy_id:
			return product_id.categ_id.removal_strategy_id.method
		loc = location_id
		while loc:
			if loc.removal_strategy_id:
				return loc.removal_strategy_id.method
			loc = loc.location_id
		return 'fifo'

	@api.model
	def _get_removal_strategy_order(self, removal_strategy):
		if removal_strategy == 'fifo':
			return 'in_date ASC NULLS FIRST, id'
		elif removal_strategy == 'fefo':
			return 'removal_date, in_date, id'
		elif removal_strategy == 'lifo':
			return 'in_date DESC NULLS LAST, id desc'
		raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

	def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
		#print ("Ingresa a _gather",self)
		#print ("Esto es product_id",product_id)
		#print ("Esto es location_id",location_id)
		self.env['stock.quant'].flush(['location_id', 'owner_id', 'package_id', 'lot_id', 'product_id'])
		self.env['product.product'].flush(['virtual_available'])
		removal_strategy = self._get_removal_strategy(product_id, location_id)
		removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
		domain = [
		('product_id', '=', product_id.id),
		]
		if not strict:
			if lot_id:
				domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
			if package_id:
				domain = expression.AND([[('package_id', '=', package_id.id)], domain])
			if owner_id:
				domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
			domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
		else:
			domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)] if lot_id else [('lot_id', '=', False)], domain])
			domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
			domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
			domain = expression.AND([[('location_id', '=', location_id.id)], domain])

		# Copy code of _search for special NULLS FIRST/LAST order
		self.check_access_rights('read')
		query = self._where_calc(domain)
		#print ("Esto es query",query)
		self._apply_ir_rules(query, 'read')
		#print ("Esto es lo que sigue de query",self._apply_ir_rules(query, 'read'))
		from_clause, where_clause, where_clause_params = query.get_sql()
		where_str = where_clause and (" WHERE %s" % where_clause) or ''
		query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + " ORDER BY "+ removal_strategy_order
		#print ("Este es el query_str final",query_str)
		self._cr.execute(query_str, where_clause_params)
		res = self._cr.fetchall()
		# No uniquify list necessary as auto_join is not applied anyways...
		quants = self.browse([x[0] for x in res])
		quants = quants.sorted(lambda q: not q.lot_id)
		return quants

	@api.model
	def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False, sale_id = None):
		self = self.sudo()
		#print("Ingresa a _get_available_quantity",sale_id)
		#print("Esto es location_id",location_id)
		#print ("Esto es self abajo context",self.env.context)
		quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
		#print ("Esto es quants",quants)
		if sale_id and quants:
			#print ("Ingresa cuando es venta")
			parametros = self.env['params.serie.point.sale.warehouse'].search([('serie_id','=',sale_id.serie_id.id),('company_id','=',sale_id.company_id.id)])
			almacenes = []
			for warehouse in parametros.warehouse_ids:
				if warehouse.status == True:
					almacenes.append(warehouse.warehouse_id.id)

			#print ("Esto es almacenes",almacenes)
			new_quants = []
			for quant in quants:
				if quant.location_id.id in almacenes:
					new_quants.append(quant.id)
			#print ("Esto es quants ahora",new_quants)
			quants = self.env['stock.quant'].search([('id','in',new_quants)])
			#print ("Esto es quants abajo ahora",quants)


		rounding = product_id.uom_id.rounding
		if product_id.tracking == 'none':
			available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
			if allow_negative:
				return available_quantity
			else:
				return available_quantity if float_compare(available_quantity, 0.0, precision_rounding=rounding) >= 0.0 else 0.0
		else:
			availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
			for quant in quants:
				if not quant.lot_id:
					availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
				else:
					availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
			if allow_negative:
				return sum(availaible_quantities.values())
			else:
				return sum([available_quantity for available_quantity in availaible_quantities.values() if float_compare(available_quantity, 0, precision_rounding=rounding) > 0])


	@api.model
	def _quant_tasks(self):
		return
		self._merge_quants()
		self._unlink_zero_quants()


	@api.model
	def _merge_quants(self):
		return
		query = """WITH
		                dupes AS (
		                    SELECT min(id) as to_update_quant_id,
		                        (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
		                        SUM(reserved_quantity) as reserved_quantity,
		                        SUM(quantity) as quantity
		                    FROM stock_quant
		                    GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id, in_date
		                    HAVING count(id) > 1
		                ),
		                _up AS (
		                    UPDATE stock_quant q
		                        SET quantity = d.quantity,
		                            reserved_quantity = d.reserved_quantity
		                    FROM dupes d
		                    WHERE d.to_update_quant_id = q.id
		                )
		           DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes)
		"""
		try:
			with self.env.cr.savepoint():
				self.env.cr.execute(query)
		except Error as e:
			_logger.info('an error occured while merging quants: %s', e.pgerror)

	@api.model
	def _unlink_zero_quants(self):
		return
		precision_digits = max(6, self.sudo().env.ref('product.decimal_product_uom').digits * 2)
		query = """SELECT id FROM stock_quant WHERE (round(quantity::numeric, %s) = 0 OR quantity IS NULL) AND round(reserved_quantity::numeric, %s) = 0;"""
		params = (precision_digits, precision_digits)
		self.env.cr.execute(query, params)
		quant_ids = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
		quant_ids.sudo().unlink()