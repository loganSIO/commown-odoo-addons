import logging
from collections import OrderedDict

from odoo import _, api, fields, models

from .common import internal_picking

_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "contract.contract"

    picking_ids = fields.One2many("stock.picking", "contract_id", string="Pickings")

    quant_ids = fields.One2many(
        "stock.quant",
        "contract_id",
        string="Contract-related stock",
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
        for record in self:
            if not record.partner_id:
                continue
            loc = record.partner_id.get_customer_location()
            record.quant_ids = record.picking_ids.mapped(
                "move_line_ids.lot_id.quant_ids"
            ).filtered(lambda q: q.quantity > 0 and q.location_id == loc)
            record.quant_nb = len(record.quant_ids)

    @api.multi
    def send_device(self, quant, date=None, do_transfer=False):
        """Create a picking of quant to partner's location.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """
        dest_location = self.partner_id.get_or_create_customer_location()
        return self._create_picking(
            [quant.lot_id],
            quant.location_id,
            dest_location,
            date=date,
            do_transfer=do_transfer,
        )

    @api.multi
    def receive_device(self, lot, dest_location, date=False, do_transfer=False):
        """Create a picking from partner's location to `dest_location`.
        If given `date` is falsy (the default), it is set to now.
        If `do_transfer` is True (default: False), execute the picking
        at the previous date.
        """

        orig_location = self.partner_id.get_or_create_customer_location()
        return self._create_picking(
            [lot], orig_location, dest_location, date=date, do_transfer=do_transfer
        )

    def _create_picking(
        self, lots, orig_location, dest_location, date=None, do_transfer=False
    ):
        self.ensure_one()
        picking = internal_picking(
            self.name,
            lots,
            orig_location,
            dest_location,
            date=date,
            do_transfer=do_transfer,
        )
        self.picking_ids |= picking
        return picking

    @api.multi
    def stock_at_date(self, date=None):
        "Return the lots at partner's location at the given date"
        self.ensure_one()

        if date is None:
            date = fields.Datetime.now()

        move_lines = self.env["stock.move.line"].search(
            [
                ("picking_id.contract_id", "=", self.id),
                ("date", "<=", date),
                ("state", "=", "done"),
            ],
            order="date ASC",
        )

        lot_ids = OrderedDict()
        partner_loc = self.partner_id.get_or_create_customer_location()
        for m in move_lines:
            lot = m.lot_id
            lot_ids.setdefault(lot.id, 0)
            lot_ids[lot.id] += m.location_dest_id == partner_loc and 1 or -1

        return self.env["stock.production.lot"].browse(
            [l_id for (l_id, total) in list(lot_ids.items()) if total > 0]
        )

    @api.multi
    def displayable_description(self):
        "Override self troubleshooting method to add device data to the description"

        result = super().displayable_description()
        devices = self.quant_ids.mapped("lot_id")

        if devices:
            devices_descr = " / ".join(
                _("%(product)s n°%(serial)s")
                % {"product": device.product_id.name, "serial": device.name}
                for device in devices
            )
            if len(devices) > 1:
                key = _("Devices")
            else:
                key = _("Device")
            result["descr"] += self.displayable_key_value(key, devices_descr)

        return result
