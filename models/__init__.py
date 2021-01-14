# -*- coding: utf-8 -*-

from datetime import datetime


def get_years_from(begining):
    """Returns dict of tuples (int, str)"""
    list_gen = list(range(begining, datetime.now().year + 1))
    list_gen.sort(reverse=True)
    years = [(year, str(year)) for year in list_gen]
    return years


def get_date_interval(o):
    """Get trimester interval switch input date
        :param o: dict
        :return tuple of date:
    """
    if o['trimester'] == 1:
        date_from = '%s-01-01' % o['year']
        date_to = '%s-03-31' % o['year']
    elif o['trimester'] == 2:
        date_from = '%s-04-01' % o['year']
        date_to = '%s-06-30' % o['year']
    elif o['trimester'] == 3:
        date_from = '%s-07-01' % o['year']
        date_to = '%s-09-30' % o['year']
    else:
        date_from = '%s-10-01' % o['year']
        date_to = '%s-12-31' % o['year']
    return date_from, date_to


from . import cnaps, hr, hr_leave, hr_payroll, iri, irsa, ostie, res_company