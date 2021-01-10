# -*- coding: utf-8 -*-

import calendar
from datetime import date, datetime, timedelta

from . import get_date_interval, get_years_from

from odoo import api, fields, models, _


class Cnaps(models.Model):
    _name = 'hr.cnaps'
    _description = 'CNaPS'
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

    @api.depends('cnaps_lines')
    def _get_total(self):
        for o in self:
            o.update({
                'total_cnaps_worker': sum(line.cnaps_worker for line in o.cnaps_lines),
                'total_cnaps_empl': sum(line.cnaps_employer for line in o.cnaps_lines),
                'total_brute_declared': sum(line.brute_declared for line in o.cnaps_lines),
                'total_brute_capped': sum(line.brute_capped for line in o.cnaps_lines)
            })
            o.cnaps_total = o.total_cnaps_worker + o.total_cnaps_empl
            o.net_total = o.cnaps_total + o.majoration - o.a_deduire

    name = fields.Char(compute='_name_get', string='Name', store=False)
    company_id = fields.Many2one('res.company', 'Denomination', required=True,
        default=lambda self: self.env.user.company_id)
    year = fields.Selection(get_years_from(2012), 'Year', required=True, default=lambda *a: datetime.now().year)
    trimester = fields.Selection(_TRIMESTER, 'Trimester', index=True, required=True)
    date_document = fields.Date('Document date', default=lambda *a: date.today())
    date_limit = fields.Date('Payment deadline', default=lambda *a: date.today() + timedelta(days=30))
    payment_mode = fields.Selection([
        (1, 'Trésor/Avis de crédit'),
        (2, 'Espèces'),
        (3, 'Chèque'),
        (4, 'Virement'),
        (5, 'Virement Postal'),
        (6, 'MVola')], 'Payment method', required=True, default=3)
    date_payment = fields.Date('Payment date', help="Payment or deposit date.")
    reference_payment = fields.Text('N°', help="Référence ou N° du règlement.")
    tresor_number = fields.Char('Chèque N°/Avis de crédit', size=40)
    espece_number = fields.Char('Espèces avec reçu N°:', size=40)
    cheque_number = fields.Char('Chèque N°:', size=40)
    transfer_number = fields.Char('Virement N°:', size=40)
    postal_transfer_number = fields.Char('Virement postal:', size=40)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'État', index=True, default='draft', readonly=True, copy=False)
    cnaps_lines = fields.One2many('hr.cnaps.line', 'cnaps_id', 'CNaPS')
    total_brute_declared = fields.Float(compute='_get_total', string="Total Salaires Déclarés",
        digits=(8, 2), store=True)
    total_brute_capped = fields.Float(compute='_get_total', string="Total Salaires Plafonnés",
        digits=(8, 2), store=True)
    total_cnaps_empl = fields.Float(compute='_get_total', string="TOTAL BASE", digits=(8, 2), store=True)
    total_cnaps_worker = fields.Float(compute='_get_total', string="TOTAL BRUTE", digits=(8, 2), store=True)
    majoration = fields.Float(string="Majoration de retard 10%", digits=(8, 2))
    solde_previous = fields.Float(string="Solde période antérieure", digits=(8, 2))
    a_deduire = fields.Float(string="Trop perçu antérieure à déduire", digits=(8, 2))
    cnaps_total = fields.Float(compute='_get_total', string="TOTAL CNaPS", digits=(8, 2), store=True)
    net_total = fields.Float(compute='_get_total', string="NET A PAYER", digits=(8, 2), store=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', _('File already exists')),
    ]

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
                slip_ids_list = []
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
                    ('state', '=', 'done'), ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)], limit=1).id
                domain_slip_id = ('slip_id', '=', slip_id)
                brute = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_1 = brute.total or 0.0

                if month_1:
                    tt = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt1 = tt.total

                    temp = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS')])
                    cnaps_worker += temp.total or 0.0

                    temp = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS_E')])
                    cnaps_employer += temp.total or 0.0

                    slip_ids_list.append(slip_id)

                month_t += 1
                date_from_temp = date_from_temp.replace(month=month_t)
                date_to = date_from_temp.replace(day=calendar.monthrange(
                    date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([
                    ('state', '=', 'done'), ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)], limit=1).id
                domain_slip_id = ('slip_id', '=', slip_id)
                brute = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_2 = brute.total or 0.0
                if month_2:
                    tt = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt2 = tt.total

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS')])
                    cnaps_worker += temp_id.total or 0.0

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS_E')])
                    cnaps_employer += temp_id.total or 0.0

                    slip_ids_list.append(slip_id)

                month_t += 1
                date_from_temp = date_from_temp.replace(month=month_t)
                date_to = date_from_temp.replace(day=calendar.monthrange(
                    date_from_temp.year, date_from_temp.month)[1])
                slip_id = slip_obj.search([
                    ('state', '=', 'done'), ('employee_id', '=', e),
                    ('date_from', '>=', date_from_temp), ('date_to', '<=', date_to)], limit=1).id
                domain_slip_id = ('slip_id', '=', slip_id)
                brute = slip_line_obj.search([domain_slip_id, ('code', '=', 'GROSS')], limit=1)
                month_3 = brute.total or 0.0
                if month_3:
                    tt = slip_line_obj.search([domain_slip_id, ('code', '=', 'DAYSIN')], limit=1)
                    tt3 = tt.total

                    temp_id = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS')])
                    cnaps_worker += temp_id.total or 0.0

                    temp = slip_line_obj.search([domain_slip_id, ('code', '=', 'CNAPS_E')])
                    cnaps_employer += temp.total or 0.0

                    slip_ids_list.append(slip_id)

                brute_declared = month_1 + month_2 + month_3
                cnaps_lines.append((0, 0, {
                    'cnaps_id': o.id,
                    'employee_id': e,
                    'slip_ids': [(6, 0, slip_ids_list)],
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
            o.write({'cnaps_lines': cnaps_lines})
        return True


class CnapsLine(models.Model):
    _name = 'hr.cnaps.line'
    _description = 'CNaPS details'

    def _name_get(self):
        for record in self:
            record.name = ''.join(['CNaPS ', str(record.cnaps_id.id), '-',
                str(record.employee_id.id), '-', str(record.id)])

    name = fields.Char(compute='_name_get', string='Name', store=False)
    cnaps_id = fields.Many2one('hr.cnaps', 'CNaPS', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    slip_ids = fields.Many2many('hr.payslip', string='Payslip', required=True)
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
