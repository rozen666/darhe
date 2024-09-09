# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, except_orm, UserError
from odoo import http
from odoo.http import request
from datetime import datetime
import calendar, math, re, io, base64, os, json, werkzeug

import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
	_inherit = 'account.payment'
	
    #FIELDS TO ACCOUNT MOVE
	number_of_document = fields.Char(string='Número de Documento', compute='_get_numer_of_document')
	
    #FUNCIONES
	def _get_numer_of_document(self):
		for x in self:
			number_of_document = None
			for move_id in x.reconciled_invoice_ids:
				number_of_document = move_id.number_of_document
			x.number_of_document = number_of_document
	