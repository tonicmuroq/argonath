# coding: utf-8

import requests
from flask import Blueprint, request, g, session, redirect, url_for

from argonath.config import OPENID_LOGIN_URL, OPENID_PROFILE_URL
from argonath.models import User
from argonath.utils import need_login

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/login/')
def login():
    if g.user:
        return redirect(url_for('index.index'))
    redir = request.host_url + 'user/login_from_openid/'
    url = '%s?redirect=%s&url=%s' % (OPENID_LOGIN_URL, redir, request.url)
    return redirect(url)


@bp.route('/logout/')
@need_login
def logout():
    session.pop('id')
    return redirect(url_for('index.index'))


@bp.route('/login_from_openid/')
def login_from_openid():
    r = requests.get(OPENID_PROFILE_URL, params={'token': request.args.get('token', '')})
    if r.status_code != 200:
        return redirect(url_for('index.index'))

    user_info = r.json()
    u = User.get_or_create(user_info['name'], user_info['email'])
    if u:
        session['id'] = u.id
    return redirect(url_for('index.index'))
