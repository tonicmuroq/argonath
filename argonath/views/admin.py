# encoding: utf-8

from flask import url_for, redirect, g, render_template, Blueprint, flash, request, abort

from argonath.utils import need_login, need_admin
from argonath.models import User, CIDR

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@need_login
def index():
    users = User.list_users(g.start, g.limit)
    return render_template('admin.html', user=g.user, users=users)

bp.route('/user_records/<username>/')
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

@bp.route('/cidrs/')
def cidrs_show():
    cidrs, total = CIDR.list_cidrs(g.start, g.limit)
    return render_template('list_cidrs.html', cidrs=cidrs, total=total, endpoint='admin.cidrs_show')

@bp.route('/cidrs/add/', methods=['GET', 'POST'])
@need_admin
def create_cidr():
    if request.method == 'GET':
        return render_template(('create_cidr.html'))
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
@need_admin
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
    print c.name
    if c:
        return render_template('cidr.html', cidr=c)
    flash('no cidr with this id', 'error')
    return redirect(url_for('admin.cidrs_show'))

@bp.route('/cidrs/<id>/edit/', methods=['GET', 'POST'])
@need_admin
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


@bp.errorhandler(403)
@bp.errorhandler(404)
def error_403_404_handler(e):
    return render_template('%s.html' % e.code), e.code

@bp.before_request
@need_admin
def access_control():
    pass
