import json

from odoo import http
from odoo.http import request
from openerp.addons.muk_rest.controllers.main import abort, check_token, ensure_db, check_params
        
class JobApiController(http.Controller):
    @http.route('/search/<string:model>', auth='none', methods=['GET'], type='http', csrf=False)
    def job_api(self, model='hr.job', token=None, **kw):
        check_params({'token': token})
        check_token()
        ensure_db()
        try:
            data = request.env[model]
            job_records = data.search([])
            job_data = []
            for record in job_records:
                job_data.append({'name': record.name, 'id': record.id})
            return json.dumps(job_data, indent=4)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)

