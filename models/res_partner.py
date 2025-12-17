# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
import base64
from io import BytesIO
import random
import string

# On gère l'import de qrcode de façon sécurisée
try:
    import qrcode
except ImportError:
    qrcode = None

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # J'ai retiré required=True pour éviter le crash des tests de paiement
    referral_code = fields.Char(string='Code Parrainage', readonly=True, copy=False)
    referral_qr_code = fields.Binary(string='QR Code Parrainage', attachment=True, readonly=True)
    referred_by_id = fields.Many2one('res.partner', string='Parrainé par')
    
    referral_count = fields.Integer(string='Nombre de filleuls', compute='_compute_referral_count', store=True)
    referral_reward_total = fields.Float(string='Total récompenses', compute='_compute_referral_reward_total', store=True)
    referral_tracking_ids = fields.One2many('referral.tracking', 'sponsor_id', string='Mes parrainages')
    is_referral_eligible = fields.Boolean(string='Éligible', compute='_compute_referral_eligible')

    @api.depends('referral_tracking_ids')
    def _compute_referral_count(self):
        for partner in self:
            partner.referral_count = len(partner.referral_tracking_ids.filtered(lambda r: r.state == 'validated'))

    @api.depends('referral_tracking_ids.reward_amount')
    def _compute_referral_reward_total(self):
        for partner in self:
            partner.referral_reward_total = sum(partner.referral_tracking_ids.filtered(lambda r: r.state == 'rewarded').mapped('reward_amount'))

    def _compute_referral_eligible(self):
        for partner in self:
            # Sécurité si le module POS n'est pas encore chargé
            if 'pos.order' not in self.env:
                partner.is_referral_eligible = False
                continue
            pos_order_count = self.env['pos.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['paid', 'done', 'invoiced'])
            ])
            partner.is_referral_eligible = pos_order_count >= 3

    def _generate_referral_code(self):
        partner_name = self.name or "CLIENT"
        # Sécurité pour éviter le crash si le nom ne contient pas de lettres
        name_part = ''.join(e for e in partner_name.upper() if e.isalnum())[:6]
        if not name_part:
            name_part = "UNK"
        
        random_part = ''.join(random.choices(string.digits, k=4))
        code = f"REF-{name_part}-{random_part}"
        
        if self.search_count([('referral_code', '=', code)]) > 0:
            return self._generate_referral_code()
        return code

    def _generate_qr_code(self, data):
        if not qrcode:
            return False
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue())
        except Exception:
            return False

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        for partner in partners:
            # On ne génère le code que si c'est un vrai client (rank > 0)
            if not partner.referral_code and partner.customer_rank > 0:
                try:
                    code = partner._generate_referral_code()
                    qr_code = partner._generate_qr_code(code)
                    partner.write({'referral_code': code, 'referral_qr_code': qr_code})
                except Exception as e:
                    _logger.error(f"Erreur parrainage: {str(e)}")
        return partners
    
    def action_view_referrals(self):
        self.ensure_one()
        return {
            'name': 'Mes Parrainages',
            'type': 'ir.actions.act_window',
            'res_model': 'referral.tracking',
            'view_mode': 'tree,form',
            'domain': [('sponsor_id', '=', self.id)],
            'context': {'default_sponsor_id': self.id}
        }
