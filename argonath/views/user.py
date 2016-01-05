# coding: utf-8

from flask import Blueprint, request, session, current_app, redirect, url_for, abort
from flask_oauthlib.client import OAuth
from argonath.utils import need_login
from argonath.models import User
from argonath import config

bp = Blueprint('user', __name__, url_prefix='/user')


oauth = OAuth(current_app)
remote = oauth.remote_app(
    'sso',
    consumer_key=config.OAUTH2_CLIENT_ID,
    consumer_secret=config.OAUTH2_CLIENT_SECRET,
    request_token_params={'scope': 'email'},
    base_url=config.OAUTH2_BASE_URL,
    request_token_url=None,
    access_token_url=config.OAUTH2_ACCESS_TOKEN_URL,
    authorize_url=config.OAUTH2_AUTHORIZE_URL,
)

@remote.tokengetter
def get_oauth_token():
    return session.get('remote_oauth')

@bp.route('/authorized')
def authorized():
    resp = remote.authorized_response()
    if resp is None:
        abort(400)
        print request.args['error_reason'], request.args['error_description']
    session['remote_oauth'] = (resp['access_token'], '')
    return redirect(url_for('user.login'))


@bp.route('/login/')
def login():
    if 'remote_oauth' in session:
        resp = remote.get('me')
        user_info = resp.data
        u = User.get_or_create(user_info['name'], user_info['email'])
        if u:
            session['id'] = u.id
        return redirect(url_for('index.index'))
    return remote.authorize(
        callback=url_for('user.authorized', _external=True)
    )


@bp.route('/logout/')
@need_login
def logout():
    session.pop('id')
    session.pop('remote_oauth')
    return redirect(url_for('index.index'))

