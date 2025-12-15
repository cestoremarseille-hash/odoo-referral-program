# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    referral_code = fields.Char(string='Code Parrainage', help="Code de parrainage saisi lors de la commande")
    is_referred = fields.Boolean(string='Commandevia parrainage', compute='_compute_is_referred', store=True)

    @api.depends('referral_code')
    def _compute_is_referred(self):
        for order in self:
            order.is_referred = bool(order.referral_code)

    def _process_referral(self):
        """Traiter le parrainage après paiement de la commande"""
        for order in self:
            if order.referral_code and order.state in ['paid', 'done', 'invoiced']:
                # Chercher le parrain avec ce code
                sponsor = self.env['res.partner'].search([
                    ('referral_code', '=', order.referral_code)
                ], limit=1)
                
                if sponsor and order.partner_id and sponsor.id != order.partner_id.id:
                    # Vérifier si le parrainage n'existe pas déjà
                    existing = self.env['referral.tracking'].search([
                        ('sponsor_id', '=', sponsor.id),
                        ('referred_id', '=', order.partner_id.id)
                    ])
                    
                    if not existing:
                        # Créer l'enregistrement de parrainage
                        self.env['referral.tracking'].create({
                            'sponsor_id': sponsor.id,
                            'referred_id': order.partner_id.id,
                            'referral_code_used': order.referral_code,
                            'pos_order_id': order.id,
                            'state': 'validated'
                        })
                        
                        # Marquer le filleul comme "parrainé par"
                        order.partner_id.write({'referred_by_id': sponsor.id})

    def write(self, vals):
        """Hook sur la modification des commandes pour traiter les parrainages"""
        res = super(PosOrder, self).write(vals)
        
        # Si la commande passe à l'état payé, traiter le parrainage
        if vals.get('state') in ['paid', 'done', 'invoiced']:
            self._process_referral()
        
        return res
