# -*- coding: utf-8 -*-
{
    'name': 'Show Foreign Currency On Aged Report (AR/AP)',
    'category': 'Accounting', 
    'author': 'Apra IT Solutions', 
    'version': '1.1',
    'license': 'LGPL-3',
    'summary': """
        Use this module if you want to show foreign currency on aged receivable & payable report.
    """, 
    'depends': ['account','account_reports'],
    'data': [ 
       'views/report_financial_views.xml',
    ],   
    'images': [
        'static/description/apra_foreign_currency_aged_report.png',
    ],

    'maintainer': 'Apra IT Solutions',
    'price': 20.00,
    'currency': 'USD',
}