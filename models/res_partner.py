# -*- coding: utf-8 -*-
from odoo import models, fields, api
import qrcode
import base64
from io import BytesIO
import random
import string

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Champs de parrainage
    referral_code = fields.Char(
        string='Code Parrainage',
        readonly=True,
        copy=False,
        help="Code unique pour parrainer d'autres clients"
    )
    referral_qr_code = fields.Binary(
        string='QR Code Parrainage',
        attachment=True,
        readonly=True,
        help="QR code généré automatiquement avec le code de parrainage"
    )
    referred_by_id = fields.Many2one(
        'res.partner',
        string='Parrainé par',
        help="Contact qui a parrainé cette personne"
    )
    referral_count = fields.Integer(
        string='Nombre de filleuls',
        compute='_compute_referral_count',
        store=True
    )
    referral_reward_total = fields.Float(
        string='Total récompenses gagnées (€)',
        compute='_compute_referral_reward_total',
        store=True
    )
    referral_tracking_ids = fields.One2many(
        'referral.tracking',
        'sponsor_id',
        string='Mes parrainages'
    )
    is_referral_eligible = fields.Boolean(
        string='Éligible au parrainage',
        compute='_compute_referral_eligible',
        help="Client avec au moins 3 achats validés"
    )

    @api.depends('referral_tracking_ids')
    def _compute_referral_count(self):
        for partner in self:
            partner.referral_count = len(partner.referral_tracking_ids.filtered(
                lambda r: r.state == 'validated'
            ))

    @api.depends('referral_tracking_ids.reward_amount')
    def _compute_referral_reward_total(self):
        for partner in self:
            partner.referral_reward_total = sum(
                partner.referral_tracking_ids.filtered(
                    lambda r: r.state == 'rewarded'
                ).mapped('reward_amount')
            )

    def _compute_referral_eligible(self):
        for partner in self:
            # Vérifier si le contact a au moins 3 commandes POS validées
            pos_order_count = self.env['pos.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['paid', 'done', 'invoiced'])
            ])
            partner.is_referral_eligible = pos_order_count >= 3

    def _generate_referral_code(self):
        """Génère un code de parrainage unique"""
        # Format: REF-NOM-XXXX (ex: REF-DUPONT-8472)
        name_part = ''.join(e for e in self.name.upper() if e.isalnum())[:6]
        random_part = ''.join(random.choices(string.digits, k=4))
        code = f"REF-{name_part}-{random_part}"
        
        # Vérifier l'unicité
        existing = self.search([('referral_code', '=', code)])
        if existing:
            return self._generate_referral_code()
        
        return code

    def _generate_qr_code(self, data):
        """Génère un QR code et retourne l'image en base64"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue())
        
        return img_base64

    @api.model_create_multi
    def create(self, vals_list):
        """Générer automatiquement le code et QR code à la création"""
        partners = super(ResPartner, self).create(vals_list)
        for partner in partners:
            if not partner.referral_code and partner.customer_rank > 0:
                # Générer le code de parrainage
                code = partner._generate_referral_code()
                qr_code = partner._generate_qr_code(code)
                
                partner.write({
                    'referral_code': code,
                    'referral_qr_code': qr_code
                })
        
        return partners

    def action_view_referrals(self):
        """Action pour voir tous les parrainages"""
        return {
            'name': 'Mes Parrainages',
            'type': 'ir.actions.act_window',
            'res_model': 'referral.tracking',
            'view_mode': 'tree,form',
            'domain': [('sponsor_id', '=', self.id)],
            'context': {'default_sponsor_id': self.id}
        }

    def send_referral_email(self):
        """Envoyer l'email de parrainage avec QR code"""
        template = self.env.ref('referral_program.mail_template_referral_program')
        if template:
            for partner in self:
                if partner.email and partner.is_referral_eligible:
                    template.send_mail(partner.id, force_send=True)
    @api.model
    def _cron_send_referral_emails(self):
        """Action planifiée pour envoyer les emails de parrainage"""
        # Chercher le tag de tracking
        tag_env = self.env['res.partner.category']
        tag_sent = tag_env.search([('name', '=', 'Email Parrainage Envoyé')], limit=1)
        
        if not tag_sent:
            tag_sent = tag_env.create({
                'name': 'Email Parrainage Envoyé',
                'color': 5
            })
        
        # Chercher les contacts éligibles qui n'ont pas encore reçu l'email
        eligible_partners = self.search([
            ('email', '!=', False),
            ('is_referral_eligible', '=', True),
            ('category_id', 'not in', [tag_sent.id])
        ], limit=200)
        
        # Envoyer les emails
        for partner in eligible_partners:
            try:
                partner.send_referral_email()
                partner.write({'category_id': [(4, tag_sent.id)]})
                _logger.info(f"Email parrainage envoyé à {partner.name}")
            except Exception as e:
                _logger.error(f"Erreur envoi email parrainage à {partner.name}: {str(e)}")

