# -*- coding: utf-8 -*-

from datetime import datetime


def get_years_from(begining):
    '''
        Returns dict of tuples (int, str)
    '''
    list_gen = list(range(begining, (datetime.now().year) + 1))
    list_gen.sort(reverse=True)
    years = [(year, str(year)) for year in list_gen]
    return years


from . import cnaps
from . import hr
from . import hr_leave
from . import hr_payroll
from . import iri
from . import irsa
from . import ostie
from . import res_company
