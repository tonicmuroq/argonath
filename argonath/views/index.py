# coding: utf-8

from flask import url_for, redirect, g, render_template, Blueprint

from argonath.utils import need_login

bp = Blueprint('index', __name__)

@bp.route('/')
def index():
    return redirect(url_for('record.list_all_records'))

@bp.route('/api-docs/')
@need_login
def profile():
    return render_template('profile.html', user=g.user)
