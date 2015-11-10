# coding: utf-8

from flask import (Blueprint, request, g, abort,
        render_template, url_for, flash, redirect)

from argonath.models import Record, CIDR
from argonath.utils import need_login
from argonath.consts import sub_domains

bp = Blueprint('record', __name__, url_prefix='/record')

@bp.route('/all/')
def list_all_records():
    records, total = Record.list_records(g.start, g.limit)
    return render_template('list_records.html', records=records,
            total=total, endpoint='record.list_all_records')

@bp.route('/mine/')
@need_login
def list_my_records():
    records, total = g.user.list_records(g.start, g.limit)
    return render_template('list_records.html', records=records,
            total=total, endpoint='record.list_my_records')

@bp.route('/<int:record_id>/')
def get_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(404)
    return render_template('record.html', record=record)

@bp.route('/search/')
def query_record():
    query = request.args.get('q', default='')
    r = Record.get_by_name(query)
    if not r:
        abort(404)
    return render_template('record.html', record=r)

@bp.route('/create/', methods=['GET', 'POST'])
@need_login
def create_record():
    if request.method == 'GET':
        return render_template('create_record.html', sub_domains=sub_domains)
    name = request.form.get('name', default='').strip()
    subname = request.form.get('subname', default='').strip()
    host_or_ip = request.form.get('host', default='').strip()

    if len(name) < 5 and not g.user.is_admin():
        flash(u'域名长度必须大于5', 'error')
        return redirect(url_for('record.create_record'))
    if '.' in name:
        flash(u'域名不能包含"."', 'error')
        return redirect(url_for('record.create_record'))
    if subname not in sub_domains:
        flash(u'不正确的子域名', 'error')
        return redirect(url_for('record.create_record'))

    domain = name + '.' + subname + '.hunantv.com'

    r = Record.get_by_domain(domain)
    if r:
        if r.can_do(g.user):
            flash(u'域名已经存在, 可以编辑', 'info')
            return redirect(url_for('record.edit_record', record_id=r.id))
        abort(403)

    r = Record.create(g.user, name, domain, host_or_ip)
    if not r:
        flash(u'创建失败', 'error')
        return redirect(url_for('record.create_record'))
    return redirect(url_for('record.get_record', record_id=r.id))

@bp.route('/<record_id>/edit/')
@need_login
def edit_record(record_id):
    record = Record.get(record_id)
    cidrs = CIDR.query.all()
    if not record:
        abort(404)
    if not record.can_do(g.user):
        abort(403)
    return render_template('edit_record.html', record=record, cidrs=cidrs)

@bp.route('/<record_id>/hosts/add/', methods=['POST'])
@need_login
def add_host_to_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(404)
    if not record.can_do(g.user):
        abort(403)
    cidr = request.form.get('cidr', default='').strip()
    host_or_ip = request.form.get('host', default='').strip()
    if not host_or_ip:
        flash(u'必须填写一个host', 'error')
        return redirect(url_for('record.edit_record', record_id=record.id))
    if not cidr:
        flash(u'Where is CIDR???', 'error')
        return redirect(url_for('record.edit_record', record_id=record.id))
    record.add_host(cidr, host_or_ip)
    return redirect(url_for('record.get_record', record_id=record.id))

@bp.route('/<record_id>/hosts/delete/', methods=['POST'])
@need_login
def delete_host_from_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(404)
    if not record.can_do(g.user):
        abort(403)

    cidr = request.form.get('cidr', default='').strip()
    host_or_ip = request.form.get('host', default='').strip()
    if not cidr:
        flash(u'没有CIDR', 'error')
        return redirect(url_for('record.edit_record', record_id=record.id))
    if not host_or_ip:
        flash(u'必须填写一个host', 'error')
        return redirect(url_for('record.edit_record', record_id=record.id))
    record.delete_host(cidr, host_or_ip)
    return redirect(url_for('record.edit_record', record_id=record.id))

@bp.route('/<record_id>/delete/', methods=['POST'])
@need_login
def delete_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(404)
    if not record.can_do(g.user):
        abort(403)
    record.delete()
    return redirect(url_for('record.list_all_records'))

@bp.errorhandler(403)
@bp.errorhandler(404)
def error_handler(e):
    return render_template('%s.html' % e.code), e.code
