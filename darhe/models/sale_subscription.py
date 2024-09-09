# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, except_orm, UserError
from odoo import http
from odoo.http import request
from datetime import datetime, date
import calendar, math, re, io, base64, os, json, werkzeug

import logging
_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit ='sale.subscription'

    
    def create_invoice_per_day(self):
        d =  datetime.date.today()
        for suscription_id in env['sale.subscription'].search([('stage_id','=',2),('recurring_next_date','=',d)]):
            move_ids = self.env['account.move'].search([('id','in',suscription_id.invoice_ids.ids),('invoice_date','=',d)])
            if not move_ids:
                move_id = self.manual_invoice()
                move_id.action_post()



    #SEND REMEMBER MAILS
    def send_remeber_mail(self, typeOfMail, dateInvoiced, move_id=None):
        # SEND BEFORE 5 DAYS
        if typeOfMail == 1:
            template_id = self.env.ref('darhe.mail_notification_before_deadline')
        
        # SEND MAIL ON DEAD LINE
        elif typeOfMail == 2:
            move_ids = self.env['account.move'].search([('id','in',self.invoice_ids.ids),('invoice_date','>=',dateInvoiced)])
            if not move_ids:
                self.manual_invoice()
            template_id = self.env.ref('darhe.mail_notification_deadline')
        
        # SEND MAIL  PAST DEAD LINE AND POST EXTRA AMOUNT
        elif typeOfMail == 3:
            # _logger.info('SEND MAIL AFTER AND ADD TAX===============>mail_notification_after_deadline : {}'.format(self.name))
            template_id = False
            # ADD ITEM EXTRA CHARGE
            if move_id.payment_state == 'not_paid':
                tax_due_id = self.env['product.product'].search([('default_code','=','int-moratorio')])
                interesMoratorio = 0
                move_id.button_draft()
                for lines in move_id.invoice_line_ids:
                    if lines.product_id.default_code != 'int-moratorio':
                        interesMoratorio = lines.price_unit*0.1

                    move_id.invoice_line_ids.create({
					'product_id' : tax_due_id.id,
					'price_unit': interesMoratorio,
					'quantity' :1,
					'move_id' : move_id.id,
					'tax_ids' : None
				})
                move_id.update({
                    'invoice_debt' : True
                })                    
                move_id.action_post()
                template_id = self.env.ref('darhe.mail_notification_after_deadline')
        else:
            return False
            # DONT'S DO ANYTHING

        if template_id:
            self.env['mail.template'].browse(template_id.id).send_mail(self.id,force_send=True)