from re import sub
import json
import traceback
import odoo
import datetime

from odoo import http, api
from odoo.http import request, Response

from openerp.addons.muk_rest.controllers.main import RESTController, REST_VERSION, ObjectEncoder, abort, LOGIN_INVALID, check_token, ensure_db, check_params

def to_nullable(dictionary):
    for key in dictionary:
        if dictionary[key] is False:
            dictionary[key] = None
        else:
            dictionary[key] = dictionary[key]
    return dictionary

def extract_data(dic, data, param):
    if (data):
        dic[param + '_id'] = data[0]
        dic[param + '_name'] = data[1]
    else:
        dic[param + '_name'] = False

def extract_id(dic, data, param):
    if (data):
        dic[param + '_id'] = data[0]

def extract_image(model_name, record_id, field_name, write_date, width=128, height=128):
    base_url = http.request.env['ir.http'].session_info()['web.base.url']
    if base_url and not base_url.endswith('/'):
        base_url = '%s/' % base_url
    if width > 0 and height > 0:
        return 'web/image/%s/%s/%s/%sx%s?unique=%s' % (
            model_name, record_id, field_name, width, height, sub('[^\d]', '', write_date))
    else:
        return 'web/image/%s/%s/%s?unique=%s' % (
            model_name, record_id, field_name, sub('[^\d]', '', write_date))

def get_data(token):
    current_user = request.env['muk_rest.token'].sudo().search([['token','=',token]])[0]
    result = request.env['hr.employee'].sudo().search_read(
        domain=[('user_id','=',current_user.user.id)],
        fields=["write_date","id","active","attendance_ids","attendance_state","birthday","company_id","department_id","job_id","last_attendance_id","last_login","leaves_count","name","image","remaining_leaves","user_id"])[0]
    extract_data(result, result["company_id"], "company")
    extract_data(result, result["department_id"], "department")
    extract_data(result, result["job_id"], "job")
    # extract_data(result, result["company_id"], "company")
    extract_data(result, result["last_attendance_id"], "last_attendance")
    extract_id(result, result["user_id"], "user")
    result['image'] = extract_image('hr.employee', result['id'], 'image', result["write_date"])
    result["tz"] = "Asia/Manila"
    result["token"] = token
    result["ip"] = request.env['ir.config_parameter'].get_param('web.base.url')
    result["expiration"] = datetime.datetime.fromtimestamp(current_user.lifetime).strftime("%Y-%m-%d %H:%M:%S")
    if (not result['birthday']):
        result['birthday'] = None
    return result

class HrisController(RESTController):

    def verify_request(self, token):
        check_params({'token': token})
        ensure_db()
        check_token()
        
    def success(self, data):
        return Response(json.dumps(data,
                            sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
    
    def error(self):
        abort({'error': traceback.format_exc()}, rollback=True, status=400) 

    @http.route('/api/hris/v1/authenticate', auth="none", type='http', methods=['POST'], csrf=False)
    def hris_authenticate(self, db=None, login=None, password=None, **kw):    
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
              
    @http.route('/api/hris/v1/session', auth="none", type='http', csrf=False)
    def get_session(self, token=None, **kw):
        self.verify_request(token)
        try:
            result = get_data(token)
            return self.success(result)
        except Exception as error:
            self.error()

    @http.route('/api/hris/', auth="none", type='http', csrf=False)
    def hris_version(self, **kw):
        REST_VERSION["hris"] = 1
        REST_VERSION["base_url"] = http.request.env['ir.http'].session_info()['web.base.url']
        return self.success(REST_VERSION)

