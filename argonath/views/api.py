# coding: utf-8

from flask import Blueprint, request, g, abort

from argonath.models import User, Record
from argonath.utils import api_need_token, jsonize
from argonath.consts import sub_domains

bp = Blueprint('api', __name__, url_prefix='/_api')

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
        abort(400, u'没有找到记录')
    return {'r': 0, 'message': 'ok', 'data': record}

@bp.route('/record/search/')
@jsonize
def query_record():
    query = request.args.get('q', type=str, default='')
    r = Record.get_by_name(query)
    if not r:
        abort(404, u'没有找到记录')
    return {'r': 0, 'message': 'ok', 'data': r}

@bp.route('/record/create/', methods=['POST'])
@jsonize
@api_need_token
def create_record():
    name = request.form.get('name', type=str, default='').strip()
    host_or_ip = request.form.get('host', type=str, default='').strip()

    # 给跪了, 不是admin就判断subname什么的
    if not g.user.is_admin():
        subname = request.form.get('subname', type=str, default='').strip()
        if len(name) < 5 and not g.user.is_admin():
            abort(400, u'域名长度必须大于5')
        if '.' in name:
            abort(400, u'域名不能包含"."')
        if subname not in sub_domains:
            abort(400, u'不正确的子域名')
        domain = name + '.' + subname + '.hunantv.com'
    # 是admin就很暴力了...
    else:
        if name.startswith('.') or name.endswith('.'):
            abort(400, u'域名不能以"."开始或者结束, 并不是dnspod啊  (￣▽￣")')
        domain = name + '.hunantv.com'

    r = Record.get_by_domain(domain)
    if r:
        abort(400, u'记录已经存在, 你可以尝试编辑')

    r = Record.create(g.user, name, domain, host_or_ip)
    if not r:
        abort(400, u'创建失败, 别问我为什么是400... o(￣ヘ￣*o)')
    return {'r': 0, 'message': 'ok', 'data': r}

@bp.route('/record/<record_id>/edit/', methods=['POST', 'PUT'])
@jsonize
@api_need_token
def edit_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(400, u'没有找到记录')
    if not record.can_do(g.user):
        abort(403, u'没有权限编辑这个记录')

    host_or_ip = request.form.get('host', type=str, default='').strip()
    if not host_or_ip:
        abort(400, u'必须填写一个host')

    record.edit(host_or_ip)
    return {'r': 0, 'message': 'ok', 'data': record}

@bp.route('/record/<record_id>/', methods=['DELETE'])
@jsonize
@api_need_token
def delete_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(404, u'没有找到记录')
    if not record.can_do(g.user):
        abort(403, u'没有权限编辑这个记录')
    record.delete()
    return {'r': 0, 'message': 'ok', 'data': None}

@bp.before_request
def init_global_vars():
    token = request.args.get('token')
    if not token:
        token = request.headers.get('token', '')
    g.user = User.get_by_token(token)

@bp.errorhandler(400)
@bp.errorhandler(403)
@jsonize
def errorhandler(error):
    return {'r': 1, 'message': error.description, 'data': None}, error.code
