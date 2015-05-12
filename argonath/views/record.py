# coding: utf-8

from flask import (Blueprint, request, g, abort,
        render_template, url_for, flash, redirect)

from argonath.models import Record
from argonath.utils import need_login

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
    query = request.args.get('q', type=str, default='')
    r = Record.get_by_name(query)
    if not r:
        abort(404)
    return render_template('record.html', record=r)

@bp.route('/create/', methods=['GET', 'POST'])
@need_login
def create_record():
    if request.method == 'GET':
        return render_template('create_record.html')
    name = request.form.get('name', type=str, default='').strip()
    host_or_ip = request.form.get('host', type=str, default='').strip()

    if len(name) < 5 and not g.user.is_admin():
        flash(u'域名长度必须大于5', 'error')
        return redirect(url_for('record.create_record'))
    if '.' in name:
        flash(u'域名不能包含"."', 'error')
        return redirect(url_for('record.create_record'))
    domain = name + '.intra.hunantv.com'
    
    r = Record.get_by_name(name)
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

@bp.route('/<record_id>/edit/', methods=['GET', 'POST'])
@need_login
def edit_record(record_id):
    record = Record.get(record_id)
    if not record:
        abort(404)
    if not record.can_do(g.user):
        abort(403)
    if request.method == 'GET':
        return render_template('edit_record.html', record=record)

    host_or_ip = request.form.get('host', type=str, default='').strip()
    if not host_or_ip:
        flash(u'必须填写一个host', 'error')
        return redirect(url_for('record.edit_record'))
    
    record.edit(host_or_ip)
    return redirect(url_for('record.get_record', record_id=record.id))

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
def error_403_404_handler(e):
    return render_template('%s.html' % e.code), e.code
