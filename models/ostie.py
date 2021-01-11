# -*- coding: utf-8 -*-

import calendar

from . import get_date_interval, get_years_from

from datetime import date, datetime, timedelta
from odoo import api, fields, models


class Ostie(models.Model):
    _name = 'hr.ostie'
    _description = 'OSTIE'
    _order = "company_id, year, trimester"
    _TRIMESTER = [
        (1, '1er Trimestre'),
        (2, '2eme Trimestre'),
        (3, '3eme Trimestre'),
        (4, '4eme Trimestre')]

    def _name_get(self):
        for record in self:
            trim_str = self._TRIMESTER[record.trimester - 1][1]
            record.name = ' '.join([str(record.year), '-', trim_str])

    @api.depends('ostie_lines')
    def _get_total(self):
        for o in self:
            o.update({
                'total_ostie_worker': sum(line.ostie_worker for line in o.ostie_lines),
                'total_ostie_empl': sum(line.ostie_employer for line in o.ostie_lines)
            })
            o.ostie_total = o.total_ostie_worker + o.total_ostie_empl
            o.net_total = o.ostie_total + o.majoration - o.a_deduire

    name = fields.Char(compute='_name_get', string='Name', store=False)
    company_id = fields.Many2one('res.company', 'Denomination', required=True,
        default=lambda self: self.env.user.company_id)
    year = fields.Selection(get_years_from(2012), 'Year', required=True, default=lambda *a: datetime.now().year)
    trimester = fields.Selection(_TRIMESTER, 'Trimester', index=True, required=True)
    date_document = fields.Date('Document date', default=lambda *a: date.today())
    date_limit = fields.Date('Payment deadline', default=lambda *a: date.today() + timedelta(days=30))
    payment_mode = fields.Selection([
        ('espece', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement Bancaire')], 'Payment method', default='cheque', required=True)
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
    total_ostie_empl = fields.Float(compute='_get_total', string="TOTAL BASE", digits=(8, 2), store=True)
    total_ostie_worker = fields.Float(compute='_get_total', string="TOTAL BRUTE", digits=(8, 2), store=True)
    majoration = fields.Float(string="Majoration de retard 10%", digits=(8, 2))
    solde_previous = fields.Float(string="Solde période antérieure", digits=(8, 2))
    a_deduire = fields.Float(string="Trop perçu antérieure à déduire", digits=(8, 2))
    ostie_total = fields.Float(compute='_get_total', string="TOTAL OSTIE", digits=(8, 2), store=True)
    net_total = fields.Float(compute='_get_total', string="NET A PAYER", digits=(8, 2), store=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ce document existe déjà!'),
    ]

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
            date_from, date_to = get_date_interval({'year': o.year, 'trimester': o.trimester})
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'cdi')]).mapped('id')
            slips = slip_obj.search([
                ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids), ('state', '=', 'done')], order="employee_id, id")
            employee_ids = []
            for slip in slips:
                if slip.employee_id.id not in employee_ids:
                    employee_ids.append(slip.employee_id.id)
            # for each employee
            for e in employee_ids:
                tt1 = 0
                tt2 = 0
                tt3 = 0
                ostie_worker = 0
                ostie_employer = 0
                date_from_temp = datetime.strptime(date_from, "%Y-%m-%d").date()
                month_t = date_from_temp.month
                date_to = date_from_temp.replace(day=calendar.monthrange(date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([
                    ('state', '=', 'done'), ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)], limit=1).id
                domain_slip_id = ('slip_id', '=', slip_id)
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
                slip_id = slip_obj.search([
                    ('state', '=', 'done'), ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)], limit=1).id
                domain_slip_id = ('slip_id', '=', slip_id)
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
                slip_id = slip_obj.search([
                    ('state', '=', 'done'), ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)]).id
                domain_slip_id = ('slip_id', '=', slip_id)
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
                    'month_2': month_2,
                    'month_3': month_3,
                    'tt1': tt1,
                    'tt2': tt2,
                    'tt3': tt3,
                    'brute_total': brute_total,
                    'ostie_worker': ostie_worker,
                    'ostie_employer': ostie_employer,
                }))
            o.write({'ostie_lines': ostie_lines})
        return True


class OstieLine(models.Model):
    _name = 'hr.ostie.line'
    _description = 'OSTIE details'

    def _name_get(self):
        for record in self:
            record.name = ''.join(['OSTIE', str(record.ostie_id.id), '-',
                str(record.employee_id.id), '-', str(record.id)])

    name = fields.Char(compute='_name_get', string='Name', store=False)
    ostie_id = fields.Many2one('hr.ostie', 'OSTIE', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
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
