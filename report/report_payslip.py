# -*- coding:utf-8 -*-

from .number import to_letters

from odoo import api, models, _


class WrappedReportPayslip(models.AbstractModel):
    _name = 'report.hr_payroll.report_payslip'
    _description = 'Report Payslip'

    def get_holidays(self):
        result = []
        pris = 0
        res = {}
        for w in self.worked_days_line_ids:
            if w.code == 'ABS':
                pris += w.number_of_days
        res = {
            'restant': self.employee_id.remaining_leaves,
            'pris': pris,
        }
        res['avant_paie'] = res['restant'] + res['pris']
        result.append(res)
        return result

    def get_net(self):
        payslip_line = self.env['hr.payslip.line']
        res = []
        ids = []
        ids = payslip_line.search([('code', '=', 'NET'), ('slip_id', '=', self.id)], limit=1)
        res = payslip_line.browse(ids) if ids else []
        return res

    def get_net_letters(self):
        # TODO: Currency variable
        payslip_line = self.get_net()
        if not payslip_line:
            raise Warning(_('It seems this is not an employee. There are no payslips.'))
        net = payslip_line.total
        if int(net) == net:
            res = to_letters(int(net))
        else:
            e = int(str(net).split('.')[0])
            d = int(str(net).split('.')[1])
            res = to_letters(e) + ' virgule ' + to_letters(d) + ' ARIARY'
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': self.ids,
            'doc_model': 'hr.payslip',
            'data': data,
            'docs': self.env['hr.payslip'].browse(self.ids),
            'get_holidays': self.get_holidays,
            'get_net': self.get_net,
            'get_net_letters': self.get_net_letters,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
