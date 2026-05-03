# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @staticmethod
    def _norm_email(email):
        return (email or "").strip().lower()

    @staticmethod
    def _norm_mobile(mobile):
        # basic normalization: remove spaces (keep + and digits as user entered)
        return (mobile or "").strip().replace(" ", "")

    @api.constrains('email', 'mobile')
    def _check_unique_email_mobile(self):
        """
        Enforce:
        - Email unique (case-insensitive) when provided
        - Mobile unique (space-insensitive) when provided

        Applies to ALL partners because Contacts can create many types of partners.
        Uses active_test=False so archived records are also checked.
        """
        Partner = self.env['res.partner'].with_context(active_test=False).sudo()

        for p in self:
            # ----- EMAIL -----
            if p.email:
                email = self._norm_email(p.email)
                dup = Partner.search([
                    ('id', '!=', p.id),
                    ('email', '=ilike', email),
                ], limit=1)
                if dup:
                    raise ValidationError(_(
                        "A contact already exists with this Email:\n"
                        "%s\n\n"
                        "Please open the existing contact instead of creating a duplicate."
                    ) % dup.display_name)

            # ----- MOBILE -----
            if p.mobile:
                mobile = self._norm_mobile(p.mobile)
                # We compare after removing spaces, but stored values may contain spaces.
                # So we do a broad search first, then normalize in python.
                candidates = Partner.search([
                    ('id', '!=', p.id),
                    ('mobile', '!=', False),
                ])
                for c in candidates:
                    if self._norm_mobile(c.mobile) == mobile:
                        raise ValidationError(_(
                            "A contact already exists with this Mobile Number:\n"
                            "%s\n\n"
                            "Please open the existing contact instead of creating a duplicate."
                        ) % c.display_name)
