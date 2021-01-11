# -*- coding:utf-8 -*-

from .number import to_letters

from odoo import _
from odoo.osv import osv
from odoo.models import AbstractModel


class InvoicePrestaReport:
    def __init__(self):
        self.localcontext.update({
            'get_payslip_lines': self.get_payslip_lines,
            'get_holidays': self.get_holidays,
            'get_net': self.get_net,
            'get_net_letters': self.get_net_letters,
        })

    def get_payslip_lines(self, obj):
        payslip_line = self.env['hr.payslip.line']
        res = []
        ids = []
        for obj_id in range(len(obj)):
            if obj[obj_id].appears_on_payslip is True:
                ids.append(obj[obj_id].id)
        if ids:
            res = payslip_line.browse(ids)
        return res

    def get_holidays(self, obj):
        result = []
        pris = 0
        for w in obj.worked_days_line_ids:
            if w.code == 'ABS':
                pris += w.number_of_days
        res = {
            'restant': obj.employee_id.remaining_leaves,
            'pris': pris,
        }
        res['avant_paie'] = res['restant'] + res['pris']
        result.append(res)
        return result

    def get_net(self):
        payslip_line = self.env['hr.payslip.line']
        ids = payslip_line.search([('code', '=', 'P_NET'), ('slip_id', '=', self.id)], limit=1)
        res = payslip_line.browse(ids) if ids else []
        return res

    def get_net_letters(self):
        # TODO: Currency variable
        payslip_line = self.get_net()
        if not payslip_line:
            raise osv.except_osv(_('Warning!'), _('This is not a subcontractor !'))
        net = payslip_line.total
        if int(net) == net:
            res = to_letters(int(net))
        else:
            e = int(str(net).split('.')[0])
            d = int(str(net).split('.')[1])
            res = to_letters(e) + ' Virgule ' + to_letters(d) + ' ARIARY'
        return res


class WrappedReportFacturePresta(AbstractModel):
    _name = 'report.l10n_mg_hr_payroll.report_facture_presta'
    _inherit = 'report.abstract_report'
    _template = 'l10n_mg_hr_payroll.report_facture_presta'
    _wrapped_report_class = InvoicePrestaReport
