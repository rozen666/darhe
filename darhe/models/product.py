# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import ustr

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.auth_signup.models.res_partner import SignupError, now
from odoo.http import request
from odoo.exceptions import AccessError

import xml.etree.ElementTree as ET
from xml.dom import minidom

import tempfile
import binascii
import xlrd

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
	_inherit = 'product.template'
	
    #FIELDS TO PRODUCT TEMPLATE
	state = fields.Selection(selection=[
		('CANCELADO','CANCELADO'),
		('DISPONIBLE','DISPONIBLE'),
		('PROB RES','PROB RES'),
		('POR RESCINDIR','POR RESCINDIR'),
		('VENDIDO','VENDIDO'),
		('V. INVERTERRENO','V. INVERTERRENO'),
		('VENDIDO INVERTERRENO','VENDIDO INVERTERRENO'),

    ], default='DISPONIBLE',
	   string='Estado')
	etapa = fields.Char(string='Etapa')
	pricem2 = fields.Float(string='Precio M2')
	m2 = fields.Float(string='M2', compute='_compute_get_m2')

	#GET M2 WITH PRICE AND PRICE M2
	def _compute_get_m2(self):
		for x in self:
			product_id = self.env['product.product'].search([('product_tmpl_id','=',x.id)], limit=1)
			try:
				x.m2 =  product_id.lst_price/x.pricem2
			except:
				x.m2 = 0
	

class UploadLayOutInitial(models.Model):
	_name = 'upload.layout.initial'
	_description='Class to upload Layouts'
	
	#FIELDS
	file = fields.Binary(string='Archivo')
	type_upload = fields.Selection(selection=[
		('producto','Producto'),
		('productom2','Producto M2'),
		('lotes','Lotes'),
		('enganche','enganche')
	])

	def floatHourToTime(self,fh):
		hours, hourSeconds = divmod(fh, 1)
		minutes, seconds = divmod(hourSeconds * 60, 1)
		return (
			int(hours),
			int(minutes),
			int(seconds * 60),
		)

    # GET VENDOR_ID OR CREATE ONE
	def getVendorId(self, name):
		partnerId = self.env['res.partner'].search([('name','=',name)])
		if partnerId :
			vendorId = self.env['res.users'].search([('partner_id','=',partnerId.id)])
		else:
			userName = ''.join(name.split(' '))
			vendorId = self.env['res.users'].create({
				'login' : '{0}@darhe.com'.format(userName),
				'password' : '{0}@darhe.com'.format(userName),
				'name' : name
			})
		return vendorId

	# GET CUSTOMER OR CREATE ONE
	def getCustomerId(self, name):
		partnerId = self.env['res.partner'].search([('name','=',name)])
		if not partnerId :
			partnerId = self.env['res.partner'].create({
				'name' : name
			})

		return partnerId

	# GET TEMPLATE FOR MONTHS IN SUSCRIPTION
	def getTemplateId(self, months):
		code = months
		if months != 'CONTADO':
			code = '{}M'.format(int(float(months)))

		templateId = self.env['sale.subscription.template'].search([('code','=',code)])
		if not templateId:
			code = '{}M'.format(int(float(months))+1)
			templateId = self.env['sale.subscription.template'].search([('code','=',code)])
			if not templateId:
				templateId = self.env['sale.subscription.template'].search([('code','=','CONTADO')])

		return templateId
	
	def create_invoices_and_payments(self, suscriptionId, count_invoices, typeInvoice,interesMoratorio):
		tax_due_id = self.env['product.product'].search([('default_code','=','int-moratorio')])
		for i in range(0,count_invoices):
			suscriptionId.manual_invoice()
			i = 0
			
			for invoiceId in suscriptionId.invoice_ids:

				for invoice_line in invoiceId.invoice_line_ids:
					invoice_line.update({
						'name' : 'Lote : {}'.format(invoice_line.product_id.name)
					})
			if typeInvoice == 'no regular':				

				invoiceId.button_draft()
				invoiceId.invoice_line_ids.create({
					'product_id' : tax_due_id.id,
					'price_unit': interesMoratorio,
					'quantity' :1,
					'move_id' : invoiceId.id,
					'tax_ids' : None
				})
			try:
				invoiceId.action_post()
			except:
				pass
			


	def convertIntToDate(self,excel_date):
		try:
			excel_date = float(excel_date)
			dt = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
			hour, minute, second = self.floatHourToTime(excel_date % 1)
			dt_t = dt.replace(hour=hour, minute=minute, second=second)
		except:
			dt_t = None
		return dt_t
	
	
	def import_initil_lote(self):
		fp = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
		fp.write(binascii.a2b_base64(self.file))
		fp.seek(0)
		
		workbook = xlrd.open_workbook(fp.name)
		sheet = workbook.sheet_by_index(0)

		pricelist_id = self.env['product.pricelist'].search([], limit=1, order='id asc')
		i = 0

		for row_no in range(sheet.nrows):
			if row_no <= 0:
				line_fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
			else:
				line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))			
				_logger.info('line:{}'.format(line))				
				
				if self.type_upload == 'producto':
					nameLote = int(float(line[0]))
					list_price = float(line[3])
					productValues = {
						'name' : nameLote,
						'etapa' : int(float(line[1])),
						'pricem2' : float(line[2]),
						'list_price' : list_price,
						'detailed_type' : line[4],
					}

					product_id = self.env['product.template'].search([('name','=',str(nameLote))])
					if not product_id:
						self.env['product.template'].create(productValues)
					else:
						if product_id.list_price <= list_price:
							product_id.update(productValues)
				
				elif self.type_upload == 'lotes':
					if not line[1]:
						continue
					nameLote = int(float(line[1]))
					product_id = self.env['product.template'].search([('name','=',str(nameLote))])
					
					if not line[13]:
						continue

					user_id = self.getVendorId(line[0])
					customer_id = self.getCustomerId(line[13])
					template_id = self.getTemplateId(line[6])
					try:
						enganche = float(line[7])
					except:
						enganche = 0
					if line[6] =='CONTADO':
						price_unit = float(line[5]) - float(enganche) 
					else:
						price_unit = (float(line[5]) - float(enganche)) / float(line[6])
					interesMoratorio = price_unit*0.1

					# dt = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date1) - 2)
					# hour, minute, second = self.floatHourToTime(excel_date1 % 1)
					date_start = self.convertIntToDate(line[12])
					try:
						date_start = date_start.replace(day=int(float(line[28])))
					except:
						date_start = self.convertIntToDate(line[12])
						

					# excel_date2 =  float(line[29])
					date_end =self.convertIntToDate(line[29])
					if not date_start:
						if not line[9] and line[9]!= '0.0':
							date_start = '2024-04-15'
						else:
							date_start = '2024-04-{}'.format(line[9])
							if date_start == '2024-04-0.0':
								date_start = '2024-04-15'

					
					comentario1 = line[15]
					comentario2 = line[45]
					# lineas de suscription					
					# orderLine = []
					orderLine = {					 
						'product_id' : product_id.id,
						'name' : 'Enganche: {}'.format(enganche),
						'price_unit' : price_unit,
						'tax_ids' : None,
					}		

					
					suscriptionId = self.env['sale.subscription'].create({
						'partner_id' : customer_id.id,
						'user_id' : user_id.id,
						'date_start' : date_start,
						'date' : date_end,
						'state_product' : line[14].strip(),
						'template_id' : template_id.id,
						'pricelist_id' : pricelist_id.id,
						'sale_subscription_line_ids' : [(0, 0, orderLine)]

					})
				
					stage_obj = self.env['sale.subscription.stage']
					if line[15] in ['CANCELADO','PROB RES']:
						stage_id = stage_obj.search([('name','=','Cerrado')])
					elif line[15] == 'DISPONIBLE':
						stage_id = stage_obj.search([('name','=','Listo para empezar')])
					else:
						stage_id = stage_obj.search([('name','=','En progreso')])
					
					suscriptionId.update({
						'stage_id' : stage_id.id,
						'date_start' : date_start,
						'recurring_next_date' : date_start,
						'date' : date_end,
					})

					suscriptionId.message_post(body=comentario1 )
					suscriptionId.message_post(body=comentario2 )
					
					#INVOICES WITHPUT
					if line[20] != '':
						pagos_regulares = int(float(line[20]))
					else:
						pagos_regulares = 0

					if line[24] !='':
						pagos_iregulares = int(float(line[24]))
					else:
						pagos_iregulares = 0
					
					# _logger.info('pagos_regulares:{}'.format(pagos_regulares))
					# _logger.info('pagos_iregulares:{}'.format(pagos_iregulares))
					# _logger.info(pmpopop)

					self.create_invoices_and_payments(suscriptionId, pagos_regulares, 'regular',interesMoratorio)
					self.create_invoices_and_payments(suscriptionId, pagos_iregulares, 'no regular',interesMoratorio)
					
					product_id.update({
						'state' : line[14].strip()
					})
				
				elif self.type_upload == 'enganche':
					fechaxls = self.convertIntToDate(line[11])

					# GET SUSCRIPTION ID
					loteNO = str(int(float(line[1])))
					partner_id = self.env['res.partner'].search([('name','=',line[13])])
					product_id = self.env['product.product'].search([('name','=',loteNO)])

					if not partner_id  or not product_id or line[7] == 'N/A':
						continue


					if not self.env["account.move"].check_access_rights("create", False):
						try:
							self.check_access_rights("write")
							self.check_access_rule("write")
						except AccessError:
							return self.env["account.move"]
					line_ids = []
					product_id = self.env['product.product'].search([('default_code','=','enganche')], limit=1)
					line_values = {
						'product_id' : product_id.id,
						'name': 'Enganche Lote: {}'.format(int(float(line[1]))),
						'quantity' : 1,
						'price_unit' : float(line[7]),
						'tax_ids' : None,
						'price_subtotal': float(line[7])							

					}
					line_ids.append((0, 0, line_values))
										
					suscriptionId = False	
					for suscriptionIds in self.env['sale.subscription'].search([('partner_id','=',partner_id.id),('product_id','=',product_id.id)]):
						# _logger.info('{} | {} '.format(suscriptionIds.product_id.name, loteNO))
						if suscriptionIds.product_id.name == loteNO:
							suscriptionId = suscriptionIds

					# _logger.info('suscriptionId ==>{}'.format(suscriptionId))

					invoice_values = suscriptionId._prepare_account_move(line_ids)
					invoice_id = (
						self.env["account.move"]
						.sudo()
						.with_context(default_move_type="out_invoice", journal_type="sale")
						.create(invoice_values)
					)
					invoice_id.update({
						'number_of_document' : 'ENGANCHE'
					})
					suscriptionId.write({"invoice_ids": [(4, invoice_id.id)]})
					invoice_id.action_post()
					# return invoice_id
				
				elif self.type_upload == 'productom2':
					# GET SUSCRIPTION ID
					loteNO = str(int(float(line[1])))
					partner_id = self.env['res.partner'].search([('name','=',line[13])])
					product_id = self.env['product.product'].search([('name','=',loteNO)])
					date_order = self.convertIntToDate(line[11])
					for suscriptionIds in self.env['sale.subscription'].search([('partner_id','=',partner_id.id),('product_id','=',product_id.id)]):
						if suscriptionIds.product_id.name == loteNO:
							suscriptionIds.update({
								'date_order' : date_order
							})
