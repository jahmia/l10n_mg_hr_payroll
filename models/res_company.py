# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    slogan = fields.Char('Slogan', size=128)
    company_registry = fields.Char('NIF', size=64)
    siret = fields.Char('STAT', size=21)
    irsa_payer = fields.Char('Nom organisme payeur', size=30, help="Nom et prénoms ou raison sociale de l'employeur ou de l'organisme payeur")
    irsa_job = fields.Many2one('hr.job', "Proffession", size=30, help="Proffession de l'organisme payeur")
    cnaps_matricule = fields.Char('Matricule', size=15)
    cnaps_activity = fields.Char('Activité', size=15)
    cnaps_regime = fields.Char('Régime', size=15)
    ostie_code_adherent = fields.Char('Code Adhérent', size=10)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _get_iban(self):
        """ return : country_code + control_key + acc_number + rib_key"""
        res = {}
        for record in self:
            country_code = record.bank_bic[4:6] if record.bank_bic else ''
            acc_number = record.acc_number.replace(' ', '')
            res[record.id] = country_code + str(record.control_key) + acc_number + str(record.rib_key)
        return res

    rib_key = fields.Integer('Clé RIB', size=2)
    control_key = fields.Integer('Clé de contrôle', size=2)
    iban = fields.Char(compute='_get_iban', size=34, string='IBAN', store=True, readonly=True)
