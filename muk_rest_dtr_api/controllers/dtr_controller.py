from re import sub
import json
import traceback
import odoo

from odoo import http, api
from odoo.http import request, Response
from ast import literal_eval
from openerp.addons.muk_rest.controllers.main import RESTController, REST_VERSION, ObjectEncoder, abort, LOGIN_INVALID, check_token, ensure_db, check_params

def get_data(token):
    current_user = request.env['muk_rest.token'].sudo().search([['token','=',token]])[0]
    return {
        "id": current_user.user.id,
        "ip": request.env['ir.config_parameter'].get_param('web.base.url'),
        "expiration":  current_user.lifetime_token(token),
        "token": token
    }

class DtrController(RESTController):

    def verify_request(self, token):
        check_params({'token': token})
        ensure_db()
        check_token()
        
    def success(self, data):
        return Response(json.dumps(data,
                            sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200,
                            headers = [
                              ('Content-Type','text/xml'),('Content-Length', str(len(data))),
                              ('Access-Control-Allow-Origin','*'),
                              ('Access-Control-Allow-Methods','POST, GET, OPTIONS'),
                              ('Access-Control-Max-Age',"1000"),
                              ('Access-Control-Allow-Headers','origin, x-csrftoken, content-type, accept'),

                    ])
    
    def error(self):
        abort({'error': traceback.format_exc()}, rollback=True, status=400) 

    @http.route('/api/dtr/v1/authenticate', auth="none", type='http', methods=['POST','OPTIONS'], csrf=False, cors="*")
    def dtr_authenticate(self, login=None, password=None, **kw):    
        check_params({'login': login, 'password': password}) 
        ensure_db()
        uid = request.session.authenticate(request.env.cr.dbname, login, password)
        if uid:
            env = api.Environment(request.env.cr, odoo.SUPERUSER_ID, {})
            token = env['muk_rest.token'].generate_token(uid)
            result = get_data(token.token)
            result["token"] = token.token
            return self.success(result)
        else:
            abort(LOGIN_INVALID, status=401)

    @http.route('/api/dtr/v1/upload/', auth="none", type='http', methods=['POST'], csrf=False)
    def dtr_upload(
        self,
        db=None, 
        token=None, 
        employee_number=None, 
        attendances=None, 
        start_period=None,
        end_period=None,
        overtime_request=None,**kw):    
        check_params({'token': token, 
        'employee_number': employee_number,
         "attendances": attendances, 
         "start_period": start_period, 
         "end_period": end_period, 
        })
        ensure_db()
        check_token()
        result = {}
        attendances = literal_eval(attendances)
        overtime_request = literal_eval(overtime_request)
        if not len(attendances) > 0:
            abort({'error': 'no attendance records'}, rollback=True, status=400)
        else:
            for attendance in attendances:
                if 'check_in' not in attendance or 'check_out' not in attendance:
                    abort({'error': 'invalid attendance value'})

        employee = request.env['hr.employee'].search([('barcode','=',employee_number)])
        if (len(employee)) == 0:
            abort({'error': 'no employee matched'}, rollback=True, status=400)
        result["notes"] = []
        try:
            employee = employee[0];
            result["overtime_id"] = None
            result["employee_id"] = employee.id
            tsheet_ids = request.env['hr_timesheet_sheet.sheet'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', start_period),
                ('date_to', '=', end_period),
            ])
            if len(tsheet_ids) == 0:
                tsheet_ids = request.env['hr_timesheet_sheet.sheet'].create({
                    'employee_id': employee.id,
                    'date_from': start_period,
                    'date_to': end_period
                })
            else:
                result["notes"].append("timesheet already exist")
                tsheet_ids = tsheet_ids[0]
                
            result["timesheet_id"] = tsheet_ids.id
            result["attendance_ids"]= []
            for attendance in attendances:
                attendance["employee_id"] = employee.id
                qres = request.env['hr.attendance'].search([
                    ('employee_id', '=', attendance['employee_id']),
                    ('check_in', '=', attendance['check_in']),
                    ('check_out', '=', attendance['check_out']),
                    ])
                attendance_existance_check = (len(qres)) == 0
                if (len(qres)) == 0:
                    attendance_id = request.env['hr.attendance'].create(attendance)
                    result["attendance_ids"].append(attendance_id.id)
                else:
                    result["attendance_ids"].append(qres[0].id)
            if len(overtime_request) > 0:
                existing = []
                for overtime in overtime_request:
                    overtime_line_id = request.env['hr.overtime.line'].search([
                        ('start_date', '=', overtime['start_date']),
                        ('start_time', '=', overtime['start_time']),
                        ('end_time', '=', overtime['end_time']),
                        ('purpose', '=', overtime['purpose']),
                    ])
                    if len(overtime_line_id) > 0:
                        existing.append(overtime_line_id[0])
                if len(existing) > 0:
                    overtime = existing[0].overtime_id
                    result['notes'].append('overtime request already exist')
                else:
                    overtime = request.env['hr.overtime'].create({
                    'ot_req_type': 'by_employee',
                    'state': 'confirm',
                    'employees': [(6,0,[employee.id])],
                    'overtime_det_ids': list(map(lambda e: (0, 0, e), overtime_request))
                })
                result["overtime_id"] = overtime.id
            return Response(json.dumps(result,
                            sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            abort({'error': traceback.format_exc()}, rollback=True, status=400)