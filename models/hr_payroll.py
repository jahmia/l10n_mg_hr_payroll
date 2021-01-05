# -*- coding: utf-8 -*-

import babel
import calendar
from datetime import datetime, time, timedelta

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
        def was_on_leave(employee_id, datetime_day):
            res = {}
            day = datetime_day.strftime("%Y-%m-%d")
            holiday_ids = self.env['hr.holidays'].search([
                ('state', '=', 'validate'), ('employee_id', '=', employee_id),
                ('type', '=', 'remove'), ('date_from', '<=', day), ('date_to', '>=', day)])
            if holiday_ids:
                res['name'] = holiday_ids.holiday_status_id.name
                if holiday_ids.holiday_status_id.deduced:
                    res['code'] = 'ABS'
                else:
                    res['code'] = 'CNG'
            return res

        res = []
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            attendances_out = {
                'name': _("Out of contract"),
                'sequence': 3,
                'code': 'OUT',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            leaves = {}
            day_from = datetime.strptime(date_from, "%Y-%m-%d")
            day_to = datetime.strptime(date_to, "%Y-%m-%d")
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                working_hours_on_day = self.env['resource.calendar'].working_hours_on_day(
                    contract.resource_calendar_id, day_from + timedelta(days=day))
                if working_hours_on_day:
                    # the employee had to work
                    leave_type = was_on_leave( contract.employee_id.id, day_from + timedelta(days=day))
                    if leave_type:
                        # if he was on leave, fill the leaves dict
                        if leave_type['name'] in leaves:
                            leaves[leave_type['name']]['number_of_days'] += 1.0
                            leaves[leave_type['name']
                                   ]['number_of_hours'] += working_hours_on_day
                        else:
                            leaves[leave_type['name']] = {
                                'name': leave_type['name'],
                                'sequence': 5,
                                'code': leave_type['code'],
                                'number_of_days': 1.0,
                                'number_of_hours': working_hours_on_day,
                                'contract_id': contract.id,
                            }
                    else:
                        # add the input vals to tmp (increment if existing)
                        date_temp = day_from + timedelta(days=day)
                        contract_date_start = datetime.strptime(
                            contract.date_start, "%Y-%m-%d")
                        # if date_temp in contract
                        condition_end = True
                        if contract.date_end:
                            if date_temp >= datetime.strptime(contract.date_end, "%Y-%m-%d"):
                                condition_end = False
                        if contract_date_start <= date_temp and condition_end:
                            attendances['number_of_days'] += 1.0
                            attendances['number_of_hours'] += working_hours_on_day
                        else:
                            attendances_out['number_of_days'] += 1.0
                            attendances_out['number_of_hours'] += working_hours_on_day
            leaves = [value for key, value in leaves.items()]
            for leave in leaves:
                if leave['code'] == 'ABS':
                    leave['number_of_days'] = 0
                    hol_obj = self.env['hr.holidays']
                    holiday_ids = hol_obj.search([
                        ('state', '=', 'validate'), ('employee_id', '=', contract.employee_id.id),
                        ('type', '=', 'remove'), ('date_from', '>=', date_from), ('date_to', '<=', date_to)])
                    for hol in holiday_ids:
                        leave['number_of_days'] += hol.number_of_days_temp
                    leave['number_of_hours'] = leave['number_of_days'] * 8
            if attendances_out['number_of_days'] > 0.0:
                res += [attendances] + leaves + [attendances_out]
            else:
                res += [attendances] + leaves
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
            'name': _('Salary Slip of %s for %s')% (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),
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
