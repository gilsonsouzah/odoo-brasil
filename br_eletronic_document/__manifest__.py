{  # pylint: disable=C8101,C8103
    'name': 'Odoo Next - Eletronic documents',
    'description': 'Enable Eletronic Documents',
    'version': '12.0.1.0.4',
    'category': 'Localization',
    'author': 'Trustcode',
    'license': 'OEEL-1',
    'website': 'http://www.odoo-next.com,br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
    ],
    'depends': [
        'br_account',
        'br_base',
        'br_base_address',
        'br_automated_payment',
    ],
    'data': [
        'data/nfe.cfop.csv',
        'data/account.cnae.csv',
        'data/account.service.type.csv',
        'data/nfe_cron.xml',
        'security/ir.model.access.csv',
        'security/eletronic_security.xml',
        'views/res_company.xml',
        'views/account_move.xml',
        'views/eletronic_document.xml',
        'views/eletronic_document_line.xml',
        'views/nfe.xml',
        'views/nfe_inutilization.xml',
        'views/base_account.xml',
        'views/fiscal_position.xml',
        'views/account_config_settings.xml',
        'views/res_partner.xml',
        'wizard/cancel_nfe.xml',
        'wizard/carta_correcao_eletronica.xml',
        'wizard/export_nfe.xml',
        'wizard/inutilize_nfe_numeration.xml',
        'reports/danfse_sao_paulo.xml',
        'reports/danfse_florianopolis.xml',
        'reports/danfse_bh.xml',
        'reports/danfe_report.xml',
    ],
}
