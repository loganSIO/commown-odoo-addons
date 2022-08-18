{
    "name": "Rental product",
    "category": "Sale",
    "summary": "Define products as rental products",
    "version": "12.0.1.0.1",
    "description": """Rental products have a fixed deposit and recurring price, displayed on the product page""",
    "author": "Commown SCIC SAS",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "base_automation",
        "contract_payment_auto",
        "contract_payment_mode",
        "document",
        "ir_attachment_lang",
        "product_contract",
        "website_sale",
    ],
    "external_dependencies": {},
    "data": [
        "views/contract.xml",
        "views/portal_contract.xml",
        "views/payment_transaction.xml",
        "views/product_template.xml",
        "views/sale_order.xml",
        "views/website_sale_templates.xml",
    ],
    "demo": ["demo/data.xml"],
    "installable": True,
}
