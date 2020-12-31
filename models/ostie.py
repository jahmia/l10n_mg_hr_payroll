# -*- coding: utf-8 -*-

import calendar
import datetime
import logging

from . import get_years_from

from datetime import date
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Ostie(models.Model):
    _name = 'hr.ostie'
    _description = 'OSTIE'
    _order = "company_id, year, trimestre"
    _TRIMESTRE = [
        (1, '1er Trimestre'),
        (2, '2eme Trimestre'),
        (3, '3eme Trimestre'),
        (4, '4eme Trimestre')]

    def _name_get(self):
        res = {}
        for record in self:
            trim_str = self.env['hr.ostie']._TRIMESTRE[record.trimestre - 1][1]
            res[record.id] = str(record.year) + ' - ' + trim_str
        return res

    def _get_total(self):
        res = {}
        for o in self:
            res[o.id] = {
                'total_ostie_worker': 0,
                'total_ostie_empl': 0,
            }
            for line in o.ostie_lines:
                res[o.id]['total_ostie_worker'] += line.ostie_worker
                res[o.id]['total_ostie_empl'] += line.ostie_employer
            res[o.id]['ostie_total'] = res[o.id]['total_ostie_worker'] + res[o.id]['total_ostie_empl']
            res[o.id]['net_total'] = res[o.id]['ostie_total'] + o.majoration - o.a_deduire
        return res

    name = fields.Char(compute='_name_get', type="char", string='Name', store=True)
    company_id = fields.Many2one('res.company', 'Dénomination', required=True, default=lambda self: self.env.user.company_id)
    year = fields.Selection(get_years_from(2012), 'Année', required=True)
    trimestre = fields.Selection(_TRIMESTRE, 'Trimestre', index=True, required=True)
    date_document = fields.Date('Date du document')
    date_limit = fields.Date('Date limite de paiement')
    payment_mode = fields.Selection([
        ('espece', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement Bancaire')], 'Mode de paiement', default='espece', required=True)
    cheque_number = fields.Char('Chèque N°', size=40)
    bank_transfer = fields.Char('Virement Bancaire N°', size=40)
    bank = fields.Char('Banque', size=40)
    voucher_number_1 = fields.Char('Numéro récipissé déclaration', size=40)
    voucher_number_2 = fields.Char('Numéro reçu de paiement', size=40)
    voucher_number_date = fields.Date('du')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'État', index=True, default='draft', readonly=True, copy=False)
    ostie_lines = fields.One2many('hr.ostie.line', 'ostie_id', 'OSTIE')
    total_ostie_empl = fields.Float(compute='_get_total', multi='total', string="TOTAL BASE", digits=(8, 2), store=True)
    total_ostie_worker = fields.Float(compute='_get_total', multi='total', string="TOTAL BRUTE", digits=(8, 2), store=True)
    ostie_total = fields.Float(compute='_get_total', multi='total', string="TOTAL OSTIE", digits=(8, 2), store=True)
    majoration = fields.Float(string="Majoration de retard 10%", digits=(8, 2))
    solde_previous = fields.Float(string="Solde période antérieure", digits=(8, 2))
    a_deduire = fields.Float(string="Trop perçu antérieure à déduire", digits=(8, 2))
    net_total = fields.Float(compute='_get_total', multi='total', string="NET A PAYER", digits=(8, 2), store=True)

    _defaults = {
        'year': lambda *a: datetime.datetime.now().year,
        'date_document': lambda *a: datetime.datetime.now(),
        'date_limit': lambda *a: date.today() + datetime.timedelta(days=30),
    }

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ce document existe déjà!'),
    ]

    @api.onchange('trimestre')
    def onchange_trismestre(self):
        line_obj = self.env['hr.ostie.line']
        lines_ids = line_obj.search([('ostie_id', 'in', self.id)])
        lines_ids.unlink()

    def ostie_confirm(self):
        return self.write({'state': 'waiting'})

    def ostie_payed(self):
        return self.write({'state': 'done'})

    def ostie_generate(self):
        f_line_obj = self.env['hr.ostie.line']
        slip_obj = self.env['hr.payslip']
        slip_line_obj = self.env['hr.payslip.line']
        ostie_lines = []
        for o in self:
            old_f_lines = f_line_obj.search([('ostie_id', '=', o.id)])
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
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'cdi')]).mapped('id')
            slip_ids = slip_obj.search([
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids),
                ('state', '=', 'done')], order="employee_id, id")
            employee_ids = []
            for slip in slip_ids:
                if slip.employee_id.id not in employee_ids:
                    employee_ids.append(slip.employee_id.id)
            # for each employee
            for e in employee_ids:
                tt1 = 0
                tt2 = 0
                tt3 = 0
                ostie_worker = 0
                ostie_employer = 0
                date_from_temp = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
                month_t = date_from_temp.month
                date_to = date_from_temp.replace(day=calendar.monthrange(date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([
                    ('id', 'in', slip_ids.mapped('id')),
                    ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp),
                    ('date_to', '<=', date_to)]).mapped('id')
                domain_slip_id = ('slip_id', 'in', slip_id)
                brute = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_1 = brute.total or 0.0
                if month_1:
                    tt = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt1 = tt.total or 0.0

                    temp_obj = slip_line_obj.search([domain_slip_id, ('code', '=', 'OSTIE')])
                    ostie_worker += temp_obj.total or 0.0

                    temp_obj = slip_line_obj.search([domain_slip_id, ('code', '=', 'OSTIE_E')])
                    ostie_employer += temp_obj.total or 0.0

                month_t += 1
                date_from_temp = date_from_temp.replace(month=month_t)
                date_to = date_from_temp.replace(day=calendar.monthrange(date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([('id', 'in', slip_ids.mapped('id')), ('employee_id', '=', e), ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)])
                domain_slip_id = ('slip_id', 'in', slip_id)
                brute = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_2 = brute.total or 0.0
                if month_2:
                    tt = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt2 = tt.total or 0.0

                    temp_obj = slip_line_obj.search([domain_slip_id, ('code', '=', 'OSTIE')])
                    ostie_worker += temp_obj.total or 0.0

                    temp_obj = slip_line_obj.search([domain_slip_id, ('code', '=', 'OSTIE_E')])
                    ostie_employer += temp_obj.total or 0.0

                month_t += 1
                date_from_temp = date_from_temp.replace(month=month_t)
                date_to = date_from_temp.replace(day=calendar.monthrange(date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([('id', 'in', slip_ids.mapped('id')), ('employee_id', '=', e), ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)]).mapped('id')
                domain_slip_id = ('slip_id', 'in', slip_id)
                brute = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_3 = brute.total or 0.0
                if month_3:
                    tt = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt3 = tt.total or 0
                    temp_obj = slip_line_obj.search([domain_slip_id, ('code', '=', 'OSTIE')])
                    ostie_worker += temp_obj.total or 0.0

                    temp_obj = slip_line_obj.search([domain_slip_id, ('code', '=', 'OSTIE_E')])
                    ostie_employer += temp_obj.total or 0.0

                brute_total = month_1 + month_2 + month_3
                ostie_lines.append((0, 0, {
                    'ostie_id': o.id,
                    'employee_id': e,
                    'month_1': month_1,
                    'tt1': tt1,
                    'month_2': month_2,
                    'tt2': tt2,
                    'month_3': month_3,
                    'tt3': tt3,
                    'brute_total': brute_total,
                    'ostie_worker': ostie_worker,
                    'ostie_employer': ostie_employer,
                }))
            o.write({'ostie_lines': ostie_lines})
        return True


class OstieLine(models.Model):
    _name = 'hr.ostie.line'
    _description = 'OSTIE'

    def _name_get(self):
        res = {}
        for record in self:
            res[record.id] = 'OSTIE' + str(record.ostie_id.id) + '-' + str(record.employee_id.id) + '-' + str(record.id)
        return res

    name = fields.Char(compute='_name_get', type="char", string='Name', store=True)
    ostie_id = fields.Many2one('hr.ostie', 'OSTIE', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    month_1 = fields.Float('Month 1', digits=(8, 2), required=True)
    month_2 = fields.Float('Month 2', digits=(8, 2), required=True)
    month_3 = fields.Float('Month 3', digits=(8, 2), required=True)
    tt1 = fields.Integer('Temps de travail, 1er mois')
    tt2 = fields.Integer('Temps de travail, 2e mois')
    tt3 = fields.Integer('Temps de travail, 3e mois')
    brute_total = fields.Float('Total Salaire Brute', digits=(8, 2))
    ostie_worker = fields.Float('OSTIE Trav.', digits=(8, 2), required=True)
    ostie_employer = fields.Float('OSTIE Empl.', digits=(8, 2), required=True)
    observation = fields.Char('Observation', size=120)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
