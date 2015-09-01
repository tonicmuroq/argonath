#!/usr/bin/env python
# encoding: utf-8

from flask import Blueprint, request, g, render_template, url_for, flash, redirect

from argonath.models import Record
from argonath.utils import need_admin


bp = Blueprint('admin_record', __name__, url_prefix='/admin/record')


@bp.route('/create/', methods=['GET', 'POST'])
def create():
    if request.method == 'GET':
        return render_template('admin_record_create.html')
    name = request.form.get('name', type=str, default='').strip()
    host_or_ip = request.form.get('host', type=str, default='').strip()

    if len(name) < 3:
        flash(u'域名长度必须大于3', 'error')
        return redirect(url_for('admin_record.create'))
    if '.' in name:
        flash(u'域名不能包含"."', 'error')
        return redirect(url_for('admin_record.create'))

    domain = '{0}.hunantv.com'.format(name)

    r = Record.get_by_domain(domain)
    if r:
        flash(u'域名已经存在, 可以编辑', 'info')
        return redirect(url_for('record.edit_record', record_id=r.id))

    r = Record.create(g.user, name, domain, host_or_ip)
    if not r:
        flash(u'创建失败', 'error')
        return redirect(url_for('admin_record.create'))
    return redirect(url_for('record.get_record', record_id=r.id))


@bp.route('/mine/')
def list_my_records():
    records, total = g.user.list_records(g.start, g.limit)
    return render_template('list_records.html', records=records,
                           total=total, endpoint='admin_record.list_my_records')


@bp.before_request
@need_admin
def access_control():
    pass
