# encoding: utf-8

from flask import url_for, redirect, g, render_template, Blueprint, flash, request, abort

from argonath.utils import need_admin
from argonath.models import User, Record, CIDR, health_check

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
def index():
    users = User.list_users(g.start, g.limit)
    return render_template('admin.html', user=g.user, users=users)

@bp.route('/create/', methods=['GET', 'POST'])
def create_record():
    if request.method == 'GET':
        return render_template('admin_record.html')

    domain = request.form.get('name', default='').strip()
    host_or_ip = request.form.get('host', default='').strip()
    comment = request.form.get('comment', default='').strip()

    if domain.startswith('.') or domain.endswith('.'):
        flash(u'域名不能以"."开始或者结束, 并不是dnspod啊 (￣▽￣")', 'error')
        return redirect(url_for('admin.create_record'))

    r = Record.get_by_domain(domain)
    if r:
        flash(u'域名已经存在, 可以编辑', 'info')
        return redirect(url_for('record.edit_record', record_id=r.id))

    r = Record.create(g.user, domain, domain, host_or_ip, comment)
    if not r:
        flash(u'创建失败', 'error')
        return redirect(url_for('admin.create_record'))

    return redirect(url_for('record.get_record', record_id=r.id))

@bp.route('/list/')
def list_my_records():
    records, total = g.user.list_records(g.start, g.limit)
    return render_template('admin_list.html',
            records=records, total=total, endpoint='admin.list_my_records')

@bp.route('/user_records/<username>/')
def user_records(username):
    user = User.get_by_name(username)
    return render_template('user_records.html', user=user)

@bp.route('/transfer/<username>/', methods=['POST'])
def transfer(username):
    source_user = User.get_by_name(username)
    User.transfer(source_user, g.user)
    flash(u'转移了{0}的域名'.format(username))
    return redirect(url_for('admin.index'))

@bp.route('/cidrs/')
def cidrs_show():
    cidrs, total = CIDR.list_cidrs(g.start, g.limit)
    return render_template('list_cidrs.html', cidrs=cidrs, total=total, endpoint='admin.cidrs_show')

@bp.route('/cidrs/add/', methods=['GET', 'POST'])
def create_cidr():
    if request.method == 'GET':
        return render_template('create_cidr.html')

    name = request.form.get('name', default='').strip()
    cidr = request.form.get('cidr', default='').strip()

    c = CIDR.get_by_name(name)
    if c:
        flash(u'Network name already exist.', 'info')
        return redirect(url_for('admin.create_cidr'))

    r = CIDR.create(name, cidr)
    if not r:
        flash(u'创建失败', 'error')
        return redirect(url_for('admin.create_cidr'))
    return redirect(url_for('admin.get_cidr', id=r.id))

@bp.route('/cidrs/<id>/delete/', methods=['POST'])
def delete_cidr(id):
    c = CIDR.get(id)
    if not c:
        abort(404)
    if c.is_default():
        abort(400)
    c.delete()
    return redirect(url_for('admin.cidrs_show'))

@bp.route('/cidrs/<id>/')
def get_cidr(id):
    c = CIDR.get(id)
    if c:
        return render_template('cidr.html', cidr=c)
    flash('no cidr with this id', 'error')
    return redirect(url_for('admin.cidrs_show'))

@bp.route('/cidrs/<id>/edit/', methods=['GET', 'POST'])
def edit_cidr(id):
    c = CIDR.get(id)
    if not c:
        abort(404)
    if c.is_default():
        abort(400)
    if request.method == 'GET':
        return render_template('edit_cidr.html', cidr=c)
    name = request.form.get('name', default='').strip()
    cidr = request.form.get('cidr', default='').strip()
    result = c.edit(name=name, cidr=cidr)
    if not result:
        flash("edit failure", 'error')
        return redirect(url_for('admin.edit_cidr', id=c.id))
    flash("edit success", 'info')
    return redirect(url_for('admin.get_cidr', id=c.id))

@bp.route('/health/', methods=['GET'])
def health():
    health_info = health_check()
    return render_template('health.html', health_info=health_info)

@bp.errorhandler(403)
@bp.errorhandler(404)
def error_handler(e):
    return render_template('%s.html' % e.code), e.code

@bp.before_request
@need_admin
def access_control():
    pass
