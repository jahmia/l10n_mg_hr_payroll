# -*- coding:utf-8 -*-

from odoo.models import AbstractModel


class IrsaReport():

    def __init__(self):
        self.localcontext.update({
            'get_month': self.get_month,
            # 'get_all_psi': self.get_all_psi,
            # 'get_all_psf': self.get_all_psf,
        })

    def get_month(self, month):
        month_str = self.env['hr.irsa']._MONTH[month][1]
        if month_str[0] not in ('A', 'O'):
            res = "DE " + month_str
        else:
            res = "D'" + month_str
        return res

    # TODO: Verify if PSI and PSF are applied
    '''def get_all_psi(self, lines):
        num = 0
        res = []
        for line in lines:
            if line.code == 'PSI':
                num += 1
                t = {'num': num, 'n_p':line.employee_id.name, 'amount': line.amount}
                res.append(t)
        return res

    def get_all_psf(self, lines):
        num = 0
        res = []
        for line in lines:
            if line.code == 'PSF':
                num += 1
                t = {'num': num, 'n_p':line.employee_id.name, 'amount': line.amount}
                res.append(t)
        return res'''


class WrappedReportIrsa(AbstractModel):
    _name = 'report.l10n_mg_hr_payroll.report_irsa'
    _inherit = 'report.abstract_report'
    _template = 'l10n_mg_hr_payroll.report_irsa'
    _wrapped_report_class = IrsaReport
