# -*- coding: utf-8 -*-

import simplejson

from odoo.http import request, route
from odoo.addons.web.controllers.main import ReportController


class PTReportController(ReportController):
    @route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        requestcontent = simplejson.loads(data)
        url, file_format = requestcontent[0], requestcontent[1]

        assert file_format == 'qweb-pdf'
        reportname = url.split('/report/pdf/')[1].split('?')[0]
        reportname, docids = reportname.split('/')

        assert docids
        model_obj = request.env['hr.payslip']
        r_obj = model_obj.browse(int(docids))

        filename = 'PT_' + r_obj.name

        response = ReportController().report_download(data, token)
        response.headers.set(
            'Content-Disposition',
            'attachment; filename=%s.pdf;' % filename)
        return response

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
