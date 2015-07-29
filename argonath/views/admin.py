# encoding: utf-8

from flask import url_for, redirect, g, render_template, Blueprint, flash, request

from argonath.utils import need_login, need_admin
from argonath.models import User, Record

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@need_login
def index():
    users = User.list_users(g.start, g.limit)
    return render_template('admin.html', user=g.user, users=users)

@bp.route('/create/', methods=['GET', 'POST'])
@need_login
def create_record():
    if request.method == 'GET':
        return render_template('admin_record.html')
    name = request.form.get('name', type=str, default='').strip()
    host_or_ip = request.form.get('host', type=str, default='').strip()
    if len(name) < 3:
        flash(u'域名长度必须大于3', 'error')
        return redirect(url_for('admin.create_record'))
    if name.startswith('.') or name.endswith('.'):
        flash(u'域名不能以"."开始或者结束, 并不是dnspod啊 (￣▽￣")', 'error')
        return redirect(url_for('admin.create_record'))
 
    domain = name + '.hunantv.com'
 
    r = Record.get_by_domain(domain)
    if r:
        flash(u'域名已经存在, 可以编辑', 'info')
        return redirect(url_for('record.edit_record', record_id=r.id))
    r = Record.create(g.user, name, domain, host_or_ip)
    if not r:
        flash(u'创建失败', 'error')
        return redirect(url_for('admin.create_record'))
    return redirect(url_for('record.get_record', record_id=r.id))

@bp.route('/list/')
@need_login
def list_my_records():
    records, total = g.user.list_records(g.start, g.limit)
    admin_records = [r for r in records if r.domain.split('.')[1] == 'hunantv']
    return render_template('admin_list.html', records=admin_records, total=total, endpoint='admin.list_my_records')

@bp.route('/user_records/<username>/')
@need_login
def user_records(username):
    user = User.get_by_name(username)
    return render_template('user_records.html', user=user)

@bp.route('/transfer/<username>/', methods=['POST'])
@need_login
def transfer(username):
    source_user = User.get_by_name(username)
    target_user = g.user
    User.transfer(source_user, target_user)
    flash(u'已经把{0}域名全部搞过来了'.format(username))
    return redirect(url_for('admin.index'))

@bp.errorhandler(403)
@bp.errorhandler(404)
def error_403_404_handler(e):
    return render_template('%s.html' % e.code), e.code

@bp.before_request
@need_admin
def access_control():
    pass
