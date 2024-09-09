# -*- coding: utf-8 -*-
{
    'name': 'Darhe Cobranza',
    'summary': """App crete to Darhe Process.""",
    'description': """
Darhe Cobranza
========
App to make task about finance in Darhe company.
    """,
    'version': '15.0.1.0',
    'author': 'Tecnologías Cosmme',
    'website': 'http://www.company.com',
    'category': 'Finance',
    'depends': [
        'base',
        'web',
        'account',
        'subscription_oca'
    ],
    'data': [
        ## Data
        'data/email_template.xml',

        ## Security
        # 'security/ir.model.access.csv',

        ## Report
        'reports/amotization_report_template.xml',
        
        ## Wizard
        # 'wizards/my_model_name_wizard.xml',
        
        ## View
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/product.xml',
        'views/menus.xml',
    ],
    'demo': [
        ## Demo Data
        #'demo/my_model_name_demo.xml',
    ],
    'icon': '/darhe/static/description/icon.png',
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'price': 0,
    'currency': 'MXN',
    'license': 'OPL-1',
    'contributors': [
        'Luis Ortega <https://github.com/rozen666>',
    ],
}
