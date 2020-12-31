# -*- coding: utf-8 -*-

import calendar
import logging

from . import get_years_from

from datetime import datetime
from odoo import fields, models

_logger = logging.getLogger(__name__)


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
        res = {}
        for record in self:
            month_str = self.env['hr.irsa']._MONTH[record.month - 1][1]
            res[record.id] = month_str + ' ' + str(record.year)
        return res

    def _get_total(self):
        res = {}
        for f in self:
            res[f.id] = {
                'base_total': 0,
                'brute_total': 0,
                'child_number_total': 0,
                'cnaps_total_worker': 0,
                'ostie_total_worker': 0,
                'cnaps_total_employer': 0,
                'ostie_total_employer': 0,
                'net_total': 0,
                'irsa_total': 0,
            }
            for line in f.irsa_lines:
                res[f.id]['base_total'] += line.base
                res[f.id]['brute_total'] += line.brute
                res[f.id]['child_number_total'] += line.child_number
                res[f.id]['cnaps_total_worker'] += line.cnaps_worker
                res[f.id]['ostie_total_worker'] += line.ostie_worker
                res[f.id]['cnaps_total_employer'] += line.cnaps_employer
                res[f.id]['ostie_total_employer'] += line.ostie_employer
                res[f.id]['net_total'] += line.net
                res[f.id]['irsa_total'] += line.irsa
        return res

    name = fields.Char(compute='_name_get', type="char",
                       string='Name', store=True)
    company_id = fields.Many2one('res.company', 'Dénomination', required=True)
    year = fields.Selection(get_years_from(2012), 'Année', required=True)
    month = fields.Selection(_MONTH, 'Mois', index=True, required=True)
    semestre = fields.Selection(
        [(1, '1er Semestre'), (2, '2eme Semestre')], 'Semestre')
    date_document = fields.Date('Date du document')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'État', index=True, readonly=True, copy=False)
    irsa_lines = fields.One2many('hr.irsa.line', 'irsa_id', 'IRSA lines')
    base_total = fields.Float(
        compute='_get_total', multi='total', string="TOTAL BASE", digits=(8, 2), store=True)
    brute_total = fields.Float(
        compute='_get_total', multi='total', string="TOTAL BRUTE", digits=(8, 2), store=True)
    child_number_total = fields.Integer(
        compute='_get_total', multi='total', string="Total Nombre d'enfants", store=True)
    cnaps_total_worker = fields.Float(
        compute='_get_total', multi='total', string="Total CNaPS T", digits=(8, 2), store=True)
    ostie_total_worker = fields.Float(
        compute='_get_total', multi='total', string="Total OSTIE T", digits=(8, 2), store=True)
    cnaps_total_employer = fields.Float(
        compute='_get_total', multi='total', string="Total CNaPS E", digits=(8, 2), store=True)
    ostie_total_employer = fields.Float(
        compute='_get_total', multi='total', string="Total OSTIE E", digits=(8, 2), store=True)
    net_total = fields.Float(compute='_get_total', multi='total',
                             string="Total Salaire NET", digits=(8, 2), store=True)
    irsa_total = fields.Float(
        compute='_get_total', multi='total', string="TOTAL IRSA", digits=(8, 2), store=True)

    _defaults = {
        'company_id': lambda self: self.env.user.company_id,
        'year': lambda *a: datetime.now().year,
        'month': lambda *a: datetime.now().month,
        'date_document': lambda *a: datetime.now(),
        'state': 'draft',
    }

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
            date_to = '%s-%s-%s' % (f.year, month,
                                    calendar.monthrange(f.year, f.month)[1])
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'cdi')])
            # for each employee
            slip_ids = slip_obj.search([
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids),
                ('state', '=', 'done')])
            for slip in slip_ids:
                Base = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'BASIC')], limit=1)
                base = Base.total

                Brute = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'GROSS')], limit=1)
                brute = Brute.total

                CnapsWorker = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'CNAPS')], limit=1)
                cnaps_worker = CnapsWorker.total

                CnapsEmployer = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'CNAPS_E')], limit=1)
                cnaps_employer = CnapsEmployer.total

                OstieWorker = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'OSTIE')], limit=1)
                ostie_worker = OstieWorker.total

                OstieEmployer = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'OSTIE_E')], limit=1)
                ostie_employer = OstieEmployer.total

                Net = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'NET')], limit=1)
                net = Net.total

                Irsa = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'IRSA')], limit=1)
                irsa = Irsa.total

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

    def onchange_month(self, month):
        if month in (1, 2, 3, 4, 5, 6):
            res = {'value': {'semestre': 1}}
        else:
            res = {'value': {'semestre': 2}}
        return res


class IrsaLine(models.Model):
    _name = 'hr.irsa.line'
    _description = 'IRSA'

    def _name_get(self):
        res = {}
        for record in self:
            res[record.id] = 'IRSA'.join(
                (str(record.id), '-', str(record.slip_id.id), '/', str(record.employee_id.id)))
        return res

    name = fields.Char(compute='_name_get', type="char",
                       string='Name', store=True)
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
