# coding: utf-8
# Copyright (C) 2018 - Today: Commown (https://commown.fr)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Website sale affiliate portal',
    'category': 'Website',
    'version': '10.0.0.0.1',
    'author': "Commown SCIC SAS",
    'license': "AGPL-3",
    'website': "https://commown.fr",
    'depends': [
        'website_sale_affiliate_product_restriction',
    ],
    'data': [
        'views/website_portal_sale_templates.xml',
        'views/sale_affiliate.xml',
    ],
    'installable': True,
}