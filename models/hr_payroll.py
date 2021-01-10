# -*- coding: utf-8 -*-

import babel
import calendar
from datetime import datetime, time
from pytz import timezone

from . import get_years_from

from odoo import api, fields, models, tools, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    name = fields.Char('Contract Reference', required=False)
    ift = fields.Float('IFT', digits=(8, 2), help="Indemnité de Transport Forfaitaire")

    @api.model
    def create(self, values):
        sequence_obj = self.env['ir.sequence']
        seq_number = sequence_obj.next_by_code('hr.contract')
        values['name'] = seq_number
        return super(HrContract, self).create(values)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    h_sup = fields.Float('Heures Supp.', digits=(7, 2), help="Heures Supplémentaires de l'employé pour le mois en cours")
    prime = fields.Float('Prime du mois', digits=(7, 2), help="Prime de l'employé pour le mois en cours")
    bonus = fields.Float('Bonus du mois', digits=(7, 2), help="Bonus du prestataire pour le mois en cours")
    acompte = fields.Float('Acompte anticipé', digits=(7, 2), help="Acompte anticipé")
    cdi = fields.Boolean('Is an employee')

    # rewrite for holidays code
    # TODO: Update to actual version
    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.name or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] += hours / work_hours

            # compute worked days
            work_data = contract.employee_id.get_work_days_data(day_from, day_to, calendar=contract.resource_calendar_id)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }

            res.append(attendances)
            res.extend(leaves.values())
        return res

    # rewrite for fields visibility and bug on v8
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        res = {
            'value': {
                'line_ids': [],
                # delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                # delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
                # 'details_by_salary_head':[], TODO: put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        cdi = True if employee.employee_type == 'cdi' else False  # + Added by Jahmia
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),
            'company_id': employee.company_id.id,
            'cdi': cdi,  # Added by Jahmia
        })

        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({'struct_id': struct.id})
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res


class Funhece(models.Model):
    _name = 'hr.funhece'
    _description = 'Funheces'
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
        (12, 'Décembre')
    ]

    def _name_get(self):
        for record in self:
            month_str = self._MONTH[record.month - 1][1]
            record.name = ' '.join((month_str, str(record.year)))

    def _get_total_ps(self):
        res = {}
        for f in self:
            res[f.id] = {'psi_total': 0.0,
                         'psf_total': 0.0, 'nb_psi': 0, 'nb_psf': 0}
            for line in f.funheces:
                if line.code == 'PSI':
                    res[f.id]['psi_total'] += line.amount
                    res[f.id]['nb_psi'] += 1
                else:  # line.code == 'PSF'
                    res[f.id]['psf_total'] += line.amount
                    res[f.id]['nb_psf'] += 1
            res[f.id]['total'] = res[f.id]['psi_total'] + res[f.id]['psf_total']
        return res

    name = fields.Char(compute='_name_get', string='Name', store=False)
    company_id = fields.Many2one('res.company', 'Denomination', required=True)
    year = fields.Selection(get_years_from(2012), 'Year', required=True)
    month = fields.Selection(_MONTH, 'Month', index=True, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'To Pay'),
        ('done', 'Payed'), ], 'Status', index=True, readonly=True, copy=False)
    funheces = fields.One2many('hr.funhece.line', 'funhece_id', 'Funhece')
    nb_psi = fields.Integer(compute='_get_total_ps', string="PSI", store=True)
    nb_psf = fields.Integer(compute='_get_total_ps', string="PSF", store=True)
    psi_total = fields.Float(compute='_get_total_ps', string="Total PSI", digits=(8, 2), store=True)
    psf_total = fields.Float(compute='_get_total_ps', string="TOTAL PSF", digits=(8, 2), store=True)
    total = fields.Float(compute='_get_total_ps', string="TOTAL", digits=(8, 2), store=True)

    _defaults = {
        'company_id': lambda self: self.env.user.company_id,
        'year': lambda *a: datetime.now().year,
        'month': lambda *a: datetime.now().month,
        'state': 'draft',
    }

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ce document existe déjà!'),
    ]

    def funhece_confirm(self):
        return self.write({'state': 'waiting'})

    def funhece_payed(self):
        return self.write({'state': 'done'})

    def funhece_generate(self):
        f_line_obj = self.env['hr.funhece.line']
        payslip_line_obj = self.env['hr.payslip.line']
        funheces = []
        total = 0
        for f in self:
            old_f_lines = f_line_obj.search([('funhece_id', '=', f.id)])
            if old_f_lines:
                old_f_lines.unlink()
            month = f.month if len(str(f.month)) == 1 else '0' + str(f.month)
            date_from = '%s-%s-01' % (f.year, month)
            date_to = '%s-%s-%s' % (f.year, month, calendar.monthrange(f.year, f.month)[1])
            employee_ids = self.env['hr.employee'].search([('employee_type', '=', 'prestataire')])
            slip_ids = self.env['hr.payslip'].search([
                ('date_from', '>=', date_from), ('date_to', '<=', date_to),
                ('employee_id', 'in', employee_ids), ('state', '=', 'done')])
            payslip_lines = payslip_line_obj.search([
                ('slip_id', 'in', slip_ids),
                ('code', 'in', ('PSI', 'PSF'))], order='employee_id')
            for line in payslip_lines:
                funheces.append((0, 0, {
                    'code': line.code,
                    'funhece_id': f.id,
                    'slip_id': line.slip_id.id,
                    'register_id': line.register_id.id,
                    'employee_id': line.employee_id.id,
                    'amount': line.total,
                }))
                total += line.total
            self.write({'funheces': funheces})
        return True


class FunheceLine(models.Model):
    _name = 'hr.funhece.line'
    _description = 'Funhece'

    def _name_get(self):
        for record in self:
            record.name = ''.join([str(record.slip_id), '/', str(record.code), '/', str('employee_id')])

    name = fields.Char(string='Name', store=False)
    funhece_id = fields.Many2one('hr.funhece', 'Funhece', required=True, ondelete='cascade', index=True)
    slip_id = fields.Many2one('hr.payslip', 'Payslip', ondelete='cascade')
    register_id = fields.Many2one('hr.contribution.register', 'Contribution Register', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    code = fields.Char('Code', required=True)
    amount = fields.Float('Amount', digits=(8, 2), required=True)
