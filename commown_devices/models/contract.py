import logging

from collections import OrderedDict

from odoo import models, fields, api

from .common import internal_picking


_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "account.analytic.account"

    picking_ids = fields.One2many(
        "stock.picking",
        "contract_id",
        string=u"Pickings")

    quant_ids = fields.One2many(
        "stock.quant", "contract_id",
        string=u"Contract-related stock",
        compute="_compute_quant_ids",
        compute_sudo=True,  # as quant.contract_id is not writable
        store=True,
        readonly=True,
    )

    quant_nb = fields.Integer(
        "Device number",
        compute="_compute_quant_ids",
        compute_sudo=True,  # for consistency with quant_ids
        default=0,
        store=True,
        index=True,
    )

    @api.depends("picking_ids.state")
    def _compute_quant_ids(self):
        for record in self.filtered("recurring_invoices"):
            loc = record.partner_id.get_customer_location()
            record.quant_ids = record.picking_ids.mapped(
                "move_lines.quant_ids").filtered(lambda q: q.location_id == loc)
            record.quant_nb = len(record.quant_ids)

    @api.multi
    def send_device(self, quant, date=None, do_transfer=False):
        """ Create a picking of quant to partner's location.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """
        dest_location = self.partner_id.get_or_create_customer_location()
        return self._create_picking(
            [quant.lot_id], quant.location_id, dest_location, date=date,
            do_transfer=do_transfer)

    @api.multi
    def receive_device(self, lot, dest_location, date=False, do_transfer=False):
        """ Create a picking from partner's location to `dest_location`.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """

        orig_location = self.partner_id.get_or_create_customer_location()
        return self._create_picking([lot], orig_location, dest_location,
                                    date=date, do_transfer=do_transfer)

    def _create_picking(self, lots, orig_location, dest_location,
                        date=None, do_transfer=False):
        self.ensure_one()
        picking = internal_picking(
            self.name, lots, orig_location, dest_location,
            date=date, do_transfer=do_transfer)
        self.picking_ids |= picking
        return picking

    @api.multi
    def stock_at_date(self, date=None):
        "Return the lots at partner's location at the given date"
        self.ensure_one()

        if date is None:
            date = fields.Datetime.now()

        moves = self.env["stock.move"].search([
            ("picking_id.contract_id", "=", self.id),
            ("date", "<=", date),
            ("state", "=", "done"),
        ], order="date ASC")

        lot_ids = OrderedDict()
        partner_loc = self.partner_id.get_or_create_customer_location()
        for m in moves:
            for l in m.mapped("lot_ids"):
                lot_ids.setdefault(l.id, 0)
                lot_ids[l.id] += m.location_dest_id == partner_loc and 1 or -1

        return self.env["stock.production.lot"].browse([
            l_id for (l_id, total) in lot_ids.items() if total > 0
        ])