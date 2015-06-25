# coding: utf-8

import json
import logging

from flask import Flask, request, g
from werkzeug.utils import import_string

from argonath.ext import db, openid2
from argonath.models import User
from argonath.utils import paginator_kwargs

blueprints = (
    'index',
    'record',
    'api',
    'admin',
)

def create_app():
    app = Flask(__name__, static_url_path='/argonath/static')
    app.config.from_object('argonath.config')
    app.secret_key = 'wolegeca'

    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                        level=logging.INFO)

    for ext in (db, openid2):
        ext.init_app(app)

    for bp in blueprints:
        import_name = '%s.views.%s:bp' % (__package__, bp)
        app.register_blueprint(import_string(import_name))

    for fl in (max, min, paginator_kwargs):
        app.add_template_global(fl)

    @app.before_request
    def init_global_vars():
        user_dict = json.loads(request.cookies.get(app.config['OPENID2_PROFILE_COOKIE_NAME'], '{}'))
        g.user = user_dict and User.get_or_create(user_dict['username'], user_dict['email']) or None
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)

    return app
