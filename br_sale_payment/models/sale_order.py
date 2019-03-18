# © 2017 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_mode_id = fields.Many2one(
        'l10n_br.payment.mode', string=u"Modo de pagamento")

    @api.multi
    def _prepare_invoice(self):
        invoice_env = self.env['account.invoice']
        vals = super(SaleOrder, self)._prepare_invoice()
        pTerm = self.payment_term_id
        payment_vals = invoice_env.prepare_preview_payment(pTerm)
        if self.payment_mode_id:
            for v in payment_vals:
                v[2]['payment_mode_id'] = self.payment_mode_id.id
        vals['preview_payment_ids'] = payment_vals
        return vals
