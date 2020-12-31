# -*- coding: utf-8 -*-
{
    'name': "Madagascar - Payroll",

    'summary': """
        Salary rules for Malagasy Companies""",

    'description': """
        * Règles salariales
        * Fiche de paie:
            * CDI
            * Prestataire
        * Contrats des employés
        * Documents Administratifs:
            * CNAPS:
                -   Employeur 13%
                -   Travailleur 1%
            * OSTIE:
                -   Employeur 5%
                -   Travailleur 1%
            * IRSA
            * IRI
            * FUNHECE:
                -   PSI: 24 000 Ar
                -   PSF: 46 000 Ar
    """,

    'author': "Mihaja ANDRIAMARO",
    'website': "https://www.linkedin.com/in/jahmia",

    'category': 'Human Resources',
    'version': '0.1',
    'sequence': 3,

    'depends': [
        'hr_payroll'
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'data/hr_payroll_sequence_data.xml',
        'data/hr_leave_data.xml',
        'views/hr_view.xml',
        'views/hr_payroll_view.xml',
        'views/irsa_view.xml',
        'views/cnaps_view.xml',
        'views/ostie_view.xml',
        'views/layouts.xml',
        'views/iri_view.xml',
        'report/hr_report.xml',
        'report/hr_payroll_report.xml',
        'report/employee_report.xml',
        'report/contract_report.xml',
        'report/payslip_report.xml',
        'report/facture_presta_report.xml',
        'report/cnaps_report.xml',
        'report/cnaps_talon_report.xml',
        'report/ostie_report.xml',
        'report/funhece_report.xml',
        'report/irsa_report.xml',
        'report/iri_report.xml',
        'report/iri_annexe_report.xml',
    ],
    'demo': [],
    'application': False
}
