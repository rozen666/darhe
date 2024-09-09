# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import ustr

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.auth_signup.models.res_partner import SignupError, now
from odoo.http import request

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
	_inherit = 'res.users'

	@api.model
	def create(self, vals):
		groupAC = []        
		for groups in self.env['res.groups'].search([('name', '=', "Limitar crear contactos")]):
			for user_1 in groups.users:
				if self.env.context.get('force_create', False):
					pass
				else:
					groupAC.append(user_1.id)
		if (self.env.user.id in groupAC) and not 'is_import' in vals:
			raise UserError(_("Lo sentimos, No cuenta con los permisos para crear Contactos"))

		return super(ResUsers, self).create(vals)