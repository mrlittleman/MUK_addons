import json
import traceback
import odoo

from odoo import http, fields
from odoo.http import request

from openerp.addons.muk_rest_hris.controllers.hris_controller import HrisController, get_data

class HrAttendanceController(HrisController):
    
    @http.route('/api/hris/v1/perform_attendance', auth="none", type='http', csrf=False)
    def v1_perform_attendance(self, token=None, **kw):
        self.verify_request(token)
        try:
            current_employee = get_data(token)
            current_date = fields.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "checked_in" in current_employee['attendance_state']:
                request.env['hr.attendance'].browse(current_employee['last_attendance_id']).write({"check_out": current_date})
            else:
                request.env['hr.attendance'].create({
                    "employee_id": current_employee["id"],
                    "check_in": current_date
                })
            return self.success(get_data(token))
        except Exception as error:
            self.error()
