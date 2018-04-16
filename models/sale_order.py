import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductRentalSaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def has_rental(self):
        self.ensure_one()
        return any(line.product_id.product_tmpl_id.is_rental
                   for line in self.order_line)