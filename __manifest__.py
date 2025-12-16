{
    'name': 'Programme de Parrainage C.E-STORE',
    'version': '1.0',    'category': 'Marketing',
    'summary': 'Programme de parrainage avec codes uniques, QR codes et récompenses automatiques',
    'description': """
Programme de Parrainage Complet
================================
* Génération automatique de codes parrainage uniques par client
* Création automatique de QR codes personnalisés
* Tracking complet parrain/filleul
* Attribution automatique des récompenses (10% pour les deux)
* Email automatique avec QR code intégré
* Dashboard de suivi des parrainages
* Intégration POS pour saisie du code parrain
    """,
    'author': 'Groupe Laboz',
    'website': 'https://www.ce-store.fr',
    'depends': [
        'base',
        'contacts',
        'point_of_sale',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/referral_tracking_views.xml',
        'views/menu.xml',
        'data/mail_template_referral.xml',
        'data/ir_cron_referral.xml',
    ],
    'external_dependencies': {
        'python': ['qrcode', 'PIL'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
