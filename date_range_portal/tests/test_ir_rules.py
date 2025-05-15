from odoo.tests import SavepointCase


class PortalDateRangeTypeIRRulesTC(SavepointCase):
    def _give_portal_access(self, partner):
        model = self.env["portal.wizard"].with_context(active_ids=[partner.id])
        portal_wizard = model.sudo().create({})
        portal_wizard.user_ids.update({"in_portal": True})
        portal_wizard.action_apply()
        self.assertTrue(partner.user_ids)
        return partner.user_ids[0]

    def test_read(self):

        partner = self.env.ref("base.res_partner_address_15")
        user = self._give_portal_access(partner)
        self.env["date.range.type"].sudo(user).search_read([], fields=["name"])
