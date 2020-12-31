# -*- coding: utf-8 -*-

import calendar
import logging
from datetime import date, datetime

from . import get_years_from

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Cnaps(models.Model):
    _name = 'hr.cnaps'
    _description = 'CNaPS'
    _order = "company_id, year, trimestre"
    _TRIMESTRE = [
        (1, '1er Trimestre'),
        (2, '2eme Trimestre'),
        (3, '3eme Trimestre'),
        (4, '4eme Trimestre')]

    def _name_get(self):
        res = {}
        for record in self:
            trim_str = self.env['hr.cnaps']._TRIMESTRE[record.trimestre - 1][1]
            res[record.id] = str(record.year) + ' - ' + trim_str
        return res

    def _get_total(self):
        res = {}
        for o in self:
            res[o.id] = {
                'total_cnaps_worker': 0,
                'total_cnaps_empl': 0,
                'total_brute_declared': 0,
                'total_brute_capped': 0,
            }
            for line in o.cnaps_lines:
                res[o.id]['total_cnaps_worker'] += line.cnaps_worker
                res[o.id]['total_cnaps_empl'] += line.cnaps_employer
                res[o.id]['total_brute_declared'] += line.brute_declared
                res[o.id]['total_brute_capped'] += line.brute_capped
            res[o.id]['cnaps_total'] = res[o.id]['total_cnaps_worker'] + \
                res[o.id]['total_cnaps_empl']
            res[o.id]['net_total'] = res[o.id]['cnaps_total'] + \
                o.majoration - o.a_deduire
        return res

    name = fields.Char(compute='_name_get', type="char",
                       string='Name', store=True)
    company_id = fields.Many2one('res.company', 'Dénomination', required=True)
    year = fields.Selection(get_years_from(2012), 'Année', required=True)
    trimestre = fields.Selection(_TRIMESTRE, 'Trimestre', index=True, required=True)
    date_document = fields.Date('Date du document')
    date_limit = fields.Date('Date limite de paiement')
    payment_mode = fields.Selection([
        (1, 'Trésor/Avis de crédit'),
        (2, 'Espèces'),
        (3, 'Chèque'),
        (4, 'Virement'),
        (5, 'Virement Postal'),
        (6, 'MVola')], 'Mode de paiement', required=True)
    date_payment = fields.Date(
        'Date de paiement', help="Date de paiement ou de versement.")
    reference_payment = fields.Text('N°', help="Référence ou N° du règlement.")
    tresor_number = fields.Char('Chèque N°/Avis de crédit', size=40)
    espece_number = fields.Char('Espèces avec reçu N°:', size=40)
    cheque_number = fields.Char('Chèque N°:', size=40)
    transfer_number = fields.Char('Virement N°:', size=40)
    postal_transfer_number = fields.Char('Virement postal:', size=40)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'État', index=True, readonly=True, copy=False)
    cnaps_lines = fields.One2many('hr.cnaps.line', 'cnaps_id', 'CNaPS')
    total_brute_declared = fields.Float(
        compute='_get_total', multi='total', string="Total Salaires Déclarés", digits=(8, 2), store=True)
    total_brute_capped = fields.Float(
        compute='_get_total', multi='total', string="Total Salaires Plafonnés", digits=(8, 2), store=True)
    total_cnaps_empl = fields.Float(
        compute='_get_total', multi='total', string="TOTAL BASE", digits=(8, 2), store=True)
    total_cnaps_worker = fields.Float(
        compute='_get_total', multi='total', string="TOTAL BRUTE", digits=(8, 2), store=True)
    cnaps_total = fields.Float(
        compute='_get_total', multi='total', string="TOTAL CNaPS", digits=(8, 2), store=True)
    majoration = fields.Float(string="Majoration de retard 10%", digits=(8, 2))
    solde_previous = fields.Float(
        string="Solde période antérieure", digits=(8, 2))
    a_deduire = fields.Float(
        string="Trop perçu antérieure à déduire", digits=(8, 2))
    net_total = fields.Float(compute='_get_total', multi='total',
                             string="NET A PAYER", digits=(8, 2), store=True)

    _defaults = {
        'year': lambda *a: datetime.now().year,
        'company_id': lambda self: self.env.user.company_id,
        'date_document': lambda *a: datetime.now(),
        'date_limit': lambda *a: date.today() + datetime.timedelta(days=30),
        'payment_mode': 2,
        'state': 'draft',
    }

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ce document existe déjà!'),
    ]

    def onchange_date(self):
        line_obj = self.env['hr.cnaps.line']
        line_ids = line_obj.search([('cnaps_id', 'in', self.id)])
        line_ids.unlink()

    def cnaps_confirm(self):
        return self.write({'state': 'waiting'})

    def cnaps_payed(self):
        return self.write({'state': 'done'})

    def cnaps_generate(self):
        f_line_obj = self.env['hr.cnaps.line']
        slip_obj = self.env['hr.payslip']
        slip_line_obj = self.env['hr.payslip.line']
        cnaps_lines = []
        for o in self:
            old_f_lines = f_line_obj.search([('cnaps_id', '=', o.id)])
            if old_f_lines:
                old_f_lines.unlink()
            if o.trimestre == 1:
                date_from = '%s-01-01' % o.year
                date_to = '%s-03-31' % o.year
            elif o.trimestre == 2:
                date_from = '%s-04-01' % o.year
                date_to = '%s-06-30' % o.year
            elif o.trimestre == 3:
                date_from = '%s-07-01' % o.year
                date_to = '%s-09-30' % o.year
            elif o.trimestre == 4:
                date_from = '%s-10-01' % o.year
                date_to = '%s-12-31' % o.year
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'cdi')])
            slip_ids = slip_obj.search([
                ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids), ('state', '=', 'done')], order="employee_id, id")
            employee_ids = []
            for slip in slip_obj.browse(slip_ids):
                if slip.employee_id.id not in employee_ids:
                    employee_ids.append(slip.employee_id.id)
            # for each employee
            for e in employee_ids:
                tt1 = 0
                tt2 = 0
                tt3 = 0
                cnaps_worker = 0
                cnaps_employer = 0
                date_from_temp = datetime.strptime(
                    date_from, "%Y-%m-%d").date()
                month_t = date_from_temp.month
                date_to = date_from_temp.replace(day=calendar.monthrange(
                    date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([
                    ('id', 'in', slip_ids),
                    ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp),
                    ('date_to', '<=', date_to)])
                domain_slip_id = ('slip_id', 'in', slip_id)
                brute_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_1 = brute_id.total or 0.0
                id_slip = slip_id
                if month_1:
                    tt_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt1 = tt_id.total

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS')])
                    cnaps_worker += temp_id.total or 0.0

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS_E')])
                    cnaps_employer += temp_id.total or 0.0

                month_t += 1
                date_from_temp = date_from_temp.replace(month=month_t)
                date_to = date_from_temp.replace(day=calendar.monthrange(
                    date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([('id', 'in', slip_ids), ('employee_id', '=', e), (
                    'date_from', '>=', date_from_temp), ('date_to', '<=', date_to)])
                domain_slip_id = ('slip_id', 'in', slip_id)
                brute_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_2 = brute_id.total or 0.0
                id_slip = slip_id or id_slip
                if month_2:
                    tt_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt2 = tt_id.total

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS')])
                    cnaps_worker += temp_id.total or 0.0

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS_E')])
                    cnaps_employer += temp_id.total or 0.0

                month_t += 1
                date_from_temp = date_from_temp.replace(month=month_t)
                date_to = date_from_temp.replace(day=calendar.monthrange(
                    date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([
                    ('id', 'in', slip_ids),
                    ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)])
                domain_slip_id = ('slip_id', 'in', slip_id)
                brute_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_3 = brute_id.total or 0.0
                id_slip = slip_id or id_slip
                if month_3:
                    tt_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt3 = tt_id.total

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS')])
                    cnaps_worker += temp_id.total or 0.0

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS_E')])
                    cnaps_employer += temp_id.total or 0.0

                brute_declared = month_1 + month_2 + month_3
                cnaps_lines.append((0, 0, {
                    'cnaps_id': o.id,
                    'employee_id': e,
                    'slip_id': id_slip[0] if id_slip else False,
                    'month_1': month_1,
                    'month_2': month_2,
                    'month_3': month_3,
                    'tt1': tt1,
                    'tt2': tt2,
                    'tt3': tt3,
                    'brute_declared': brute_declared,
                    'brute_capped': brute_declared,
                    'cnaps_worker': cnaps_worker,
                    'cnaps_employer': cnaps_employer,
                }))
            o.write(o.id, {'cnaps_lines': cnaps_lines})
        return True


class CnapsLine(models.Model):
    _name = 'hr.cnaps.line'
    _description = 'CNaPS'

    def _name_get(self):
        res = {}
        for record in self:
            res[record.id] = 'CNaPS'.join((
                str(record.cnaps_id.id), '-',
                str(record.employee_id.id), '-', str(record.id)))
        return res

    name = fields.Char(compute='_name_get', string='Name', store=True)
    cnaps_id = fields.Many2one(
        'hr.cnaps', 'CNaPS', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    slip_id = fields.Many2one('hr.payslip', 'Payslip')
    month_1 = fields.Float('Month 1', digits=(8, 2), required=True)
    month_2 = fields.Float('Month 2', digits=(8, 2), required=True)
    month_3 = fields.Float('Month 3', digits=(8, 2), required=True)
    tt1 = fields.Integer('Temps de travail, 1er mois')
    tt2 = fields.Integer('Temps de travail, 2e mois')
    tt3 = fields.Integer('Temps de travail, 3e mois')
    brute_declared = fields.Float('Salaires Déclarés', digits=(8, 2))
    brute_capped = fields.Float('Salaires Plafonnés', digits=(8, 2))
    cnaps_worker = fields.Float('CNaPS Trav.', digits=(8, 2), required=True)
    cnaps_employer = fields.Float('CNAPS Empl.', digits=(8, 2), required=True)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
