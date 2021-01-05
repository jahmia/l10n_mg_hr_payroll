# -*- coding: utf-8 -*-

import calendar
from datetime import date, datetime

from . import get_years_from

from odoo import api, fields, models


class Iri(models.Model):
    _name = 'hr.iri'
    _description = 'IRI'
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
                'net_total': sum(line.net for line in o.iri_lines),
                'iri_total': sum(line.iri for line in o.iri_lines)
            })

    name = fields.Char(compute='_name_get', string='Name', store=False)
    title = fields.Char('Titre', translate=True)
    company_id = fields.Many2one('res.company', 'Denomination', required=True, default= lambda self: self.env.user.company_id)
    signature = fields.Char('Signature', translate=True)
    year = fields.Selection(get_years_from(2012), 'Year', required=True, default=lambda *a: datetime.now().year)
    month = fields.Selection(_MONTH, 'Month', index=True, required=True, default=lambda *a: datetime.now().month)
    date_document = fields.Date('Document date', default=lambda *a: date.today())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'État', index=True, default='draft', readonly=True, copy=False)
    iri_lines = fields.One2many('hr.iri.line', 'iri_id', 'IRI lines')
    net_total = fields.Float(compute='_get_total', string="Total Prestation NET", digits=(8, 2), store=True)
    iri_total = fields.Float(compute='_get_total', string="TOTAL IRI", digits=(8, 2), store=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ce document existe déjà!'),
    ]

    def iri_confirm(self):
        return self.write({'state': 'waiting'})

    def iri_payed(self):
        return self.write({'state': 'done'})

    def iri_generate(self):
        f_line_obj = self.env['hr.iri.line']
        slip_obj = self.env['hr.payslip']
        slip_line_obj = self.env['hr.payslip.line']
        iri_lines = []
        for f in self:
            old_f_lines = f_line_obj.search([('iri_id', '=', f.id)])
            if old_f_lines:
                old_f_lines.unlink()
            month = f.month if len(str(f.month)) == 1 else '0' + str(f.month)
            date_from = '%s-%s-01' % (f.year, month)
            date_to = '%s-%s-%s' % (f.year, month, calendar.monthrange(f.year, f.month)[1])
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'prestataire')]).mapped('id')
            # for each employee
            slips = slip_obj.search([
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids),
                ('state', '=', 'done')])
            for slip in slips:
                net = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'P_NET')], limit=1)
                net = net.total

                iri = slip_line_obj.search([('slip_id', '=', slip.id), ('code', '=', 'IRI')], limit=1)
                iri = iri.total

                iri_lines.append((0, 0, {
                    'iri_id': f.id,
                    'slip_id': slip.id,
                    'employee_id': slip.employee_id.id,
                    'net': net,
                    'iri': iri,
                }))
            self.write({'iri_lines': iri_lines})
        return True

    @api.onchange('month')
    def onchange_month(self):
        self.semester = 1 if self.month in (1, 2, 3, 4, 5, 6) else 2


class IriLine(models.Model):
    _name = 'hr.iri.line'
    _description = 'IRI LINES'

    def _name_get(self):
        for record in self:
            record.name = ''.join(['IRI ', str(record.id), '-', str(record.slip_id.id), '/', str(record.employee_id.id)])

    name = fields.Char(compute='_name_get', string='Name', store=True)
    iri_id = fields.Many2one(
        'hr.iri', 'IRI ', required=True, ondelete='cascade', index=True)
    slip_id = fields.Many2one('hr.payslip', 'Payslip', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    purchase_date = fields.Date("Date de l'achat")
    net = fields.Float('Achat', digits=(8, 2), required=True)
    iri = fields.Float('IRI', digits=(8, 2), required=True)
