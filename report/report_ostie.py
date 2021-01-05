# -*- coding:utf-8 -*-

from odoo.models import AbstractModel


class WrappedReportOstie(AbstractModel):
    _name = 'report.l10n_mg_hr_payroll.report_ostie'
    _inherit = 'report.abstract_report'
    _template = 'l10n_mg_hr_payroll.report_ostie'
