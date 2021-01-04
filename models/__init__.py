# -*- coding: utf-8 -*-

from datetime import datetime


def get_years_from(begining):
    """Returns dict of tuples (int, str)"""
    list_gen = list(range(begining, (datetime.now().year) + 1))
    list_gen.sort(reverse=True)
    years = [(year, str(year)) for year in list_gen]
    return years


def get_date_interval(o):
    """Get trimestre interval switch input date
        :param o: dict
        :return tuple of date:
    """
    if o['trimestre'] == 1:
        date_from = '%s-01-01' % o['year']
        date_to = '%s-03-31' % o['year']
    elif o['trimestre'] == 2:
        date_from = '%s-04-01' % o['year']
        date_to = '%s-06-30' % o['year']
    elif o['trimestre'] == 3:
        date_from = '%s-07-01' % o['year']
        date_to = '%s-09-30' % o['year']
    else:
        date_from = '%s-10-01' % o['year']
        date_to = '%s-12-31' % o['year']
    return date_from, date_to


from . import cnaps
from . import hr
from . import hr_leave
from . import hr_payroll
from . import iri
from . import irsa
from . import ostie
from . import res_company
