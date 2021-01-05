# -*- coding: utf-8 -*-

from odoo import fields, models


class LeaveType(models.Model):
    _inherit = "hr.leave.type"

    deduced = fields.Boolean('Deduced', help='If checked, this leaves is deduced from the payslip.')
