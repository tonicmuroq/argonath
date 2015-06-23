#!/usr/bin/env python
# encoding: utf-8

from flask import url_for, redirect, g, render_template, Blueprint, flash

from argonath.utils import need_login, need_admin
from argonath.models import User

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@need_login
@need_admin
def index():
    users = User.list_users()
    return render_template('admin.html', user=g.user, users=users)


@bp.route('/user_records/<username>/')
@need_login
@need_admin
def user_records(username):
    user = User.get_by_name(username)
    return render_template('user_records.html', user=user)


@bp.route('/transfer/<username>/', methods=['POST'])
@need_login
@need_admin
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
