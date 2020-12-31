# -*- coding: utf-8 -*-

from odoo import fields, models


class LeaveType(models.Model):
    _inherit = "hr.leave.type"
    _description = "Type of leave"

    deduced = fields.Boolean('Deduced', help='If checked, this leaves is deduced from the payslip.')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
