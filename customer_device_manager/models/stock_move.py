from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _set_lot_contract(self, lots, contract, **kwargs):
        "Create Device Assignment on device expedition validation"
        super()._set_lot_contract(lots, contract, **kwargs)

        partner = contract.partner_id.commercial_partner_id
        if partner.is_company:
            for lot in lots:
                latest_assignment = self.env[
                    "customer_device_manager.device_assignment"
                ].search(
                    [
                        ("device_id", "=", lot.id),
                    ],
                    limit=1,
                )

                if (
                    latest_assignment
                    and latest_assignment.partner_id.commercial_partner_id == partner
                ):
                    self.env[
                        "customer_device_manager.device_assignment_history"
                    ].sudo().create(
                        {
                            "assignment_id": latest_assignment.id,
                            "date": fields.Datetime.now(),
                            "partner_id": latest_assignment.partner_id.id,
                            "device_location": "at_customer",
                        }
                    )

                else:
                    self.env["customer_device_manager.device_assignment"].create(
                        {
                            "device_id": lot.id,
                            "partner_id": partner.id,
                            "assignment_date": fields.Datetime.now(),
                            "device_location": "at_customer",
                        }
                    )

    def _unset_lot_contract(self, lots, contract, location_dest, **kwargs):
        "Archive Device Assignment on device return validation"
        super()._unset_lot_contract(lots, contract, location_dest, **kwargs)

        partner = contract.partner_id.commercial_partner_id
        for lot in lots:
            assignment = self.env["customer_device_manager.device_assignment"].search(
                [
                    ("device_id", "=", lot.id),
                    ("partner_id", "child_of", partner.id),
                    ("device_location", "=", "at_customer"),
                ],
                limit=1,
            )

            if assignment:
                self.env[
                    "customer_device_manager.device_assignment_history"
                ].sudo().create(
                    {
                        "assignment_id": assignment.id,
                        "date": fields.Datetime.now(),
                        "partner_id": assignment.partner_id.id,
                        "device_location": "at_commown",
                    }
                )
