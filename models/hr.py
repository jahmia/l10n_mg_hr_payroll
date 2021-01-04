# -*- coding: utf-8 -*-

import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class hr_employee(models.Model):
    _inherit = "hr.employee"

    department_id = fields.Many2one('hr.department', string='Department', required=False)
    employee_type = fields.Selection([('cdi', 'CDI'), ('prestataire', 'Prestataire')], required=True, default='cdi', string='Type Contrat')
    cin_town = fields.Char('Fait à', translate=False, help="Lieu de délivrance du CIN")
    cin_delivery = fields.Date('Le', help="Date de délivrance du CIN")
    cnaps = fields.Char('N° CNaPS', size=20)
    indice = fields.Integer('Indice', size=4)

    _sql_constraints = [
        ('identification_id_unique', 'unique (company_id, identification_id)', _('The Identification No must be unique per company !')),
        ('cnaps_number_unique', 'unique (cnaps)', _('This CNAPS is already associated to an employee !'))
    ]

    def get_employee_id(self):
        res = False
        resource = self.env['resource.resource'].search([('user_id', '=', self.env.uid)], order="id desc", limit=1)
        if resource:
            self.env.cr.execute("""
                SELECT id FROM hr_employee
                WHERE resource_id = %d
            """ % (resource[0]))
            employee = self.env.cr.dictfetchall()
            if employee:
                res = employee[0]['id']
        return res

    def department_default_get(self):
        department_id = False
        employee_id = self.get_employee_id()
        if employee_id:
            employee = self.browse(employee_id)
            department_id = employee.department_id.id
        return department_id


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
