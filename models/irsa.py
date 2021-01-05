# -*- coding: utf-8 -*-

import calendar

from . import get_years_from

from datetime import date, datetime
from odoo import api, fields, models


class Irsa(models.Model):
    _name = 'hr.irsa'
    _description = 'IRSA'
    _order = "year, month"
    _MONTH = [
        (1, 'Janvier'),
        (2, 'Février'),
        (3, 'Mars'),
        (4, 'Avril'),
        (5, 'Mai'),
        (6, 'Juin'),
        (7, 'Juillet'),
        (8, 'Août'),
        (9, 'Septembre'),
        (10, 'Octobre'),
        (11, 'Novembre'),
        (12, 'Décembre')]

    def _name_get(self):
        for record in self:
            month_str = self._MONTH[record.month - 1][1]
            record.name = ' '.join([month_str, str(record.year)])

    def _get_total(self):
        for o in self:
            o.update({
                'base_total': sum(line.base for line in o.irsa_lines),
                'brute_total': sum(line.brute for line in o.irsa_lines),
                'child_number_total': sum(line.child_number for line in o.irsa_lines),
                'cnaps_total_worker': sum(line.cnaps_worker for line in o.irsa_lines),
                'ostie_total_worker': sum(line.ostie_worker for line in o.irsa_lines),
                'cnaps_total_employer': sum(line.cnaps_employer for line in o.irsa_lines),
                'ostie_total_employer': sum(line.ostie_employer for line in o.irsa_lines),
                'net_total': sum(line.net for line in o.irsa_lines),
                'irsa_total': sum(line.irsa for line in o.irsa_lines)
            })

    name = fields.Char(compute='_name_get', string='Name', store=False)
    company_id = fields.Many2one('res.company', 'Denomination', required=True, default=lambda self: self.env.user.company_id)
    year = fields.Selection(get_years_from(2012), 'Year', required=True, default=lambda *a: datetime.now().year)
    month = fields.Selection(_MONTH, 'Month', index=True, required=True, default=lambda *a: datetime.now().month)
    semester = fields.Selection([(1, '1er Semestre'), (2, '2eme Semestre')], 'Semestre')
    date_document = fields.Date('Date du document', default=lambda *a: date.today())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'État', index=True, readonly=True, default='draft', copy=False)
    irsa_lines = fields.One2many('hr.irsa.line', 'irsa_id', 'IRSA lines')
    base_total = fields.Float(compute='_get_total', string="TOTAL BASE", digits=(8, 2), store=True)
    brute_total = fields.Float(compute='_get_total', string="TOTAL BRUTE", digits=(8, 2), store=True)
    child_number_total = fields.Integer(compute='_get_total', string="Total Nombre d'enfants", store=True)
    cnaps_total_worker = fields.Float(compute='_get_total', string="Total CNaPS T", digits=(8, 2), store=True)
    ostie_total_worker = fields.Float(compute='_get_total', string="Total OSTIE T", digits=(8, 2), store=True)
    cnaps_total_employer = fields.Float(compute='_get_total', string="Total CNaPS E", digits=(8, 2), store=True)
    ostie_total_employer = fields.Float(compute='_get_total', string="Total OSTIE E", digits=(8, 2), store=True)
    net_total = fields.Float(compute='_get_total', string="Total Salaire NET", digits=(8, 2), store=True)
    irsa_total = fields.Float(compute='_get_total', string="TOTAL IRSA", digits=(8, 2), store=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ce document existe déjà!'),
    ]

    def irsa_confirm(self):
        return self.write({'state': 'waiting'})

    def irsa_payed(self):
        return self.write({'state': 'done'})

    def irsa_generate(self):
        f_line_obj = self.env['hr.irsa.line']
        slip_obj = self.env['hr.payslip']
        slip_line_obj = self.env['hr.payslip.line']
        irsa_lines = []
        for f in self:
            old_f_lines = f_line_obj.search([('irsa_id', '=', f.id)])
            if old_f_lines:
                old_f_lines.unlink()

            month = f.month if len(str(f.month)) == 1 else '0' + str(f.month)
            date_from = '%s-%s-01' % (f.year, month)
            date_to = '%s-%s-%s' % (f.year, month, calendar.monthrange(f.year, f.month)[1])
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'cdi')]).mapped('id')
            # for each employee
            slips = slip_obj.search([
                ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids), ('state', '=', 'done')])
            for slip in slips:
                base = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'BASIC')], limit=1)
                base = base.total

                brute = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'GROSS')], limit=1)
                brute = brute.total

                cnaps_worker = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'CNAPS')], limit=1)
                cnaps_worker = cnaps_worker.total

                cnaps_employer = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'CNAPS_E')], limit=1)
                cnaps_employer = cnaps_employer.total

                ostie_worker = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'OSTIE')], limit=1)
                ostie_worker = ostie_worker.total

                ostie_obj = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'OSTIE_E')], limit=1)
                ostie_employer = ostie_obj.total

                net_obj = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'NET')], limit=1)
                net = net_obj.total

                irsa_obj = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'IRSA')], limit=1)
                irsa = irsa_obj.total

                irsa_lines.append((0, 0, {
                    'irsa_id': f.id,
                    'slip_id': slip.id,
                    'employee_id': slip.employee_id.id,
                    'job_id': slip.employee_id.job_id.id,
                    'base': base,
                    'brute': brute,
                    'child_number': slip.employee_id.children,
                    'cnaps_worker': cnaps_worker,
                    'ostie_worker': ostie_worker,
                    'cnaps_employer': cnaps_employer,
                    'ostie_employer': ostie_employer,
                    'net': net,
                    'irsa': irsa,
                }))
            self.write({'irsa_lines': irsa_lines})
        return True

    @api.onchange('month')
    def onchange_month(self):
        self.semester = 1 if self.month in (1, 2, 3, 4, 5, 6) else 2


class IrsaLine(models.Model):
    _name = 'hr.irsa.line'
    _description = 'IRSA details'

    def _name_get(self):
        for record in self:
            record.name = ''.join(['IRSA ', str(record.id), '-', str(record.slip_id.id), '/', str(record.employee_id.id)])

    name = fields.Char(compute='_name_get', string='Name', store=False)
    irsa_id = fields.Many2one(
        'hr.irsa', 'IRSA ', required=True, ondelete='cascade', index=True)
    slip_id = fields.Many2one('hr.payslip', 'Payslip', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position')
    base = fields.Float('Salaire de base', digits=(8, 2), required=True)
    brute = fields.Float('Salaire brute', digits=(8, 2), required=True)
    child_number = fields.Integer('Nombre Enfants', required=True)
    cnaps_worker = fields.Float('CNaPS Trav.', digits=(8, 2), required=True)
    ostie_worker = fields.Float('OSTIE Trav.', digits=(8, 2), required=True)
    cnaps_employer = fields.Float('CNaPS Empl.', digits=(8, 2), required=True)
    ostie_employer = fields.Float('OSTIE Empl.', digits=(8, 2), required=True)
    net = fields.Float('Net', digits=(8, 2), required=True)
    irsa = fields.Float('IRSA', digits=(8, 2), required=True)
