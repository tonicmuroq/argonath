# coding: utf-8

from flask import Blueprint, request, g, abort

from argonath.models import User, Record, Domain
from argonath.utils import api_need_token, jsonize

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
    query = request.args.get('q', default='')
    r = Record.get_by_name(query)
    if not r:
        abort(404, u'没有找到记录')
    return {'r': 0, 'message': 'ok', 'data': r}


@bp.route('/record/create/', methods=['POST'])
@jsonize
@api_need_token
def create_record():
    name = request.form.get('name', default='').strip()
    host_or_ip = request.form.get('host', default='').strip()
    comment = request.form.get('comment', default='').strip()

    # 给跪了, 不是admin就判断subname什么的
    if not g.user.is_admin():
        subname = request.form.get('subname', default='').strip()
        if len(name) < 5 and not g.user.is_admin():
            abort(400, u'域名长度必须大于5')
        if '.' in name:
            abort(400, u'域名不能包含"."')
        if not Domain.get_by_name(subname):
            abort(400, u'不正确的子域名')
        domain = '%s.%s' % (name, subname)
    # 是admin就很暴力了...
    # 可以随便传域名的哦...
    else:
        if name.startswith('.') or name.endswith('.'):
            abort(400, u'域名不能以"."开始或者结束, 并不是dnspod啊  (￣▽￣")')
        domain = name

    r = Record.get_by_domain(domain)
    if r:
        abort(400, u'记录已经存在, 你可以尝试编辑')

    r = Record.create(g.user, name, domain, host_or_ip, comment)
    if not r:
        abort(400, u'创建失败, 别问我为什么是400... o(￣ヘ￣*o)')
    return {'r': 0, 'message': 'ok', 'data': r}


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
        token = request.headers.get('X-Argonath-Token', '')
    g.user = User.get_by_token(token)


@bp.errorhandler(400)
@bp.errorhandler(403)
@jsonize
def errorhandler(error):
    return {'r': 1, 'message': error.description, 'data': None}, error.code
