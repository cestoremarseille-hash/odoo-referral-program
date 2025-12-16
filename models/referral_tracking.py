# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ReferralTracking(models.Model):
    _name = 'referral.tracking'
    _description = 'Suivi des Parrainages'
    _order = 'create_date desc'

    name = fields.Char(string='Référence', required=True, copy=False, default='New')
    sponsor_id = fields.Many2one('res.partner', string='Parrain', required=True, ondelete='cascade')
    referred_id = fields.Many2one('res.partner', string='Filleul', required=True, ondelete='cascade')
    referral_code_used = fields.Char(string='Code utilisé', required=True)
    
    pos_order_id = fields.Many2one('pos.order', string='Commande POS du filleul', ondelete='set null')
    order_date = fields.Datetime(string='Date de la commande', related='pos_order_id.date_order', store=True)
    order_amount = fields.Monetary(string='Montant de la commande', related='pos_order_id.amount_total', currency_field='currency_id', store=True)
        currency_id = fields.Many2one('res.currency', string='Devise', related='pos_order_id.currency_id', store=True)
    state = fields.Selection([
        ('pending', 'En attente'),
        ('validated', 'Validé'),
        ('rewarded', 'Récompensé'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='pending', required=True)
    
    reward_amount = fields.Float(string='Montant récompense', compute='_compute_reward_amount', store=True)
    reward_percentage = fields.Float(string='% Récompense', default=10.0)
    
    notes = fields.Text(string='Notes')
    
    @api.depends('order_amount', 'reward_percentage', 'state')
    def _compute_reward_amount(self):
        for tracking in self:
            if tracking.state == 'rewarded' and tracking.order_amount:
                tracking.reward_amount = tracking.order_amount * (tracking.reward_percentage / 100)
            else:
                tracking.reward_amount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('referral.tracking') or 'New'
        return super(ReferralTracking, self).create(vals_list)

    def action_validate(self):
        """Valider le parrainage"""
        for tracking in self:
            tracking.state = 'validated'

    def action_reward(self):
        """Attribuer les récompenses au parrain et filleul"""
        for tracking in self:
            if tracking.state != 'validated':
                raise ValidationError(_("Le parrainage doit être validé avant d'attribuer les récompenses."))
            
            # Créer des coupons de réduction de 10% pour le parrain et le filleul
            # (à implémenter selon votre système de coupons)
            
            tracking.state = 'rewarded'
            
            # Log l'attribution de la récompense
            tracking.message_post(
                body=f"Récompense de {tracking.reward_amount:.2f}€ attribuée au parrain {tracking.sponsor_id.name}"
            )

    def action_cancel(self):
        """Annuler le parrainage"""
        for tracking in self:
            tracking.state = 'cancelled'
