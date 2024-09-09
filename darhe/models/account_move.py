# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, except_orm, UserError
from odoo import http
from odoo.http import request
from datetime import datetime
import calendar, math, re, io, base64, os, json, werkzeug

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
	_inherit = 'account.move'
	
    #FIELDS TO ACCOUNT MOVE
	number_of_document = fields.Char(string='Número de Documento', default='1 de ')
	invoice_debt = fields.Boolean(string='Pago Tardío', default=False)
	

