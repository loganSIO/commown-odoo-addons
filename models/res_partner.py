import logging
from base64 import b64decode

import magic

from odoo import models, fields, tools

_logger = logging.getLogger(__name__)


class CommownPartner(models.Model):
    _inherit = 'res.partner'

    auto_widget_binary_fields = ['id_card1', 'id_card2', 'proof_of_address']

    max_doc_image_size = (1240, 1754)
    max_doc_size_Mo = 5

    _binary_field_policy = (
        "Images are resized to %dx%d and, all files are limited to %dMo."
        % (max_doc_image_size + (max_doc_size_Mo,)))

    id_card1 = fields.Binary(
        "ID card", attachment=True, store=True,
        help=("This field holds an image or PDF file to store the ID card. "
              + _binary_field_policy))

    id_card2 = fields.Binary(
        "ID card (2)", attachment=True, store=True,
        help=("This field holds an image or PDF file to store the ID card (2)."
              + _binary_field_policy))

    proof_of_address = fields.Binary(
        "Proof of address", attachment=True, store=True,
        help=("This field holds a file to store a proof of address,"
              + _binary_field_policy))

    def _apply_bin_field_size_policy(self, vals):
        """ Apply the binary field limit policy: resize images, raise if the
        final value is still too big.
        """
        for field in self.auto_widget_binary_fields:
            b64value = vals.get(field)
            if b64value:
                value = b64decode(b64value)
                if magic.from_buffer(value, mime=True).startswith('image'):
                    vals[field] = tools.image_resize_image(
                        b64value, avoid_if_small=True,
                        size=self.max_doc_image_size)
                    value = b64decode(vals[field])
                assert len(value) < 1024 * 1024 * self.max_doc_size_Mo, (
                    'Too big file for %s (%s > %dMo)'
                    % (field, len(value), self.max_doc_size_Mo))

    def create(self, vals, **kwargs):
        "Apply binary docs limit policy before creating the entity"
        self._apply_bin_field_size_policy(vals)
        return super(CommownPartner, self).create(vals, **kwargs)

    def write(self, vals, **kwargs):
        "Apply binary docs limit policy before updating the entity"
        self._apply_bin_field_size_policy(vals)
        return super(CommownPartner, self).write(vals, **kwargs)
