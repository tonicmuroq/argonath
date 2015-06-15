# coding: utf-8

from flask import Blueprint, request, g

from argonath.models import User, Record
from argonath.utils import api_need_token, jsonize
from argonath.consts import sub_domains

bp = Blueprint('api', __name__, url_prefix='/_api')

def _make_error_response(message, code):
    return {'r': 1, 'message': message, 'data': None}, code

@bp.route('/record/all/')
@jsonize
def list_all_records():
    records, _ = Record.list_records(g.start, g.limit)
    return {'r': 0, 'message': 'ok', 'data': records}

@bp.route('/record/mine/')
@jsonize
@api_need_token
def list_my_records():
    records, _ = g.user.list_records(g.start, g.limit)
    return {'r': 0, 'message': 'ok', 'data': records}

@bp.route('/record/<int:record_id>/')
@jsonize
def get_record(record_id):
    record = Record.get(record_id)
    if not record:
        return _make_error_response(u'没有找到记录', 400)
    return {'r': 0, 'message': 'ok', 'data': record}

@bp.route('/record/search/')
@jsonize
def query_record():
    query = request.args.get('q', type=str, default='')
    r = Record.get_by_name(query)
    if not r:
        return _make_error_response(u'没有找到记录', 400)
    return {'r': 0, 'message': 'ok', 'data': r}

@bp.route('/record/create/', methods=['POST'])
@jsonize
@api_need_token
def create_record():
    name = request.form.get('name', type=str, default='').strip()
    subname = request.form.get('subname', type=str, default='').strip()
    host_or_ip = request.form.get('host', type=str, default='').strip()

    if len(name) < 5 and not g.user.is_admin():
        return _make_error_response(u'域名长度必须大于5', 400)
    if '.' in name:
        return _make_error_response(u'域名不能包含"."', 400)
    if subname not in sub_domains:
        return _make_error_response(u'不正确的子域名', 400)
    domain = name + '.' + subname + '.hunantv.com'
    
    r = Record.get_by_name(name)
    if r:
        return _make_error_response(u'记录已经存在, 你可以尝试编辑', 400)

    r = Record.create(g.user, name, domain, host_or_ip)
    if not r:
        return _make_error_response(u'创建失败', 500)
    return {'r': 0, 'message': 'ok', 'data': r}

@bp.route('/record/<record_id>/edit/', methods=['POST', 'PUT'])
@jsonize
@api_need_token
def edit_record(record_id):
    record = Record.get(record_id)
    if not record:
        return _make_error_response(u'没有找到记录', 400)
    if not record.can_do(g.user):
        return _make_error_response(u'没有权限编辑这个记录', 403)

    host_or_ip = request.form.get('host', type=str, default='').strip()
    if not host_or_ip:
        return _make_error_response(u'必须填写一个host', 400)
    
    record.edit(host_or_ip)
    return {'r': 0, 'message': 'ok', 'data': record}

@bp.route('/record/<record_id>/', methods=['DELETE'])
@jsonize
@api_need_token
def delete_record(record_id):
    record = Record.get(record_id)
    if not record:
        return _make_error_response(u'没有找到记录', 400)
    if not record.can_do(g.user):
        return _make_error_response(u'没有权限编辑这个记录', 403)
    record.delete()
    return {'r': 0, 'message': 'ok', 'data': None}

@bp.before_request
def init_global_vars():
    token = request.args.get('token', type=str, default='')
    if not token:
        token = request.headers.get('token', '')
    g.user = User.get_by_token(token)
