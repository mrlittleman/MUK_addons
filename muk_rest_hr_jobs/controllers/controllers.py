import json

from odoo import http
from odoo.http import request

class JobApiController(http.Controller):
    @http.route('/api/jobs', auth='user', type='http')
    def job_api(self, **kw):
        try:
            data = request.env['hr.job']
            job_records = data.search([])
            job_data = []
            for record in job_records:
                job_data.append({'name': record.name, 'id': record.id})
            return json.dumps(job_data)
        except Exception:
            return [{'error': 'Unknown Command' }]
