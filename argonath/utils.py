# coding: utf-8

import json
import random
import string
from datetime import datetime
from functools import wraps
from flask import abort, g, redirect, Response

from argonath.ext import openid2
from argonath.models import Base

def need_login(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            return redirect(openid2.login_url)
        return f(*args, **kwargs)
    return _

def api_need_token(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            return {'r': 1, 'message': 'need token'}, 400
        return f(*args, **kwargs)
    return _

def need_admin(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            return redirect(openid2.login_url)
        if not g.user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return _

def paginator_kwargs(kw):
    d = kw.copy()
    d.pop('start', None)
    d.pop('limit', None)
    return d

def random_string(length):
    return ''.join(random.sample(string.ascii_letters + string.digits, length))

class ArgonathJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Base):
            return obj.to_dict()
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(ArgonathJSONEncoder, self).default(obj)

def jsonize(f):
    @wraps(f)
    def _(*args, **kwargs):
        r = f(*args, **kwargs)
        if isinstance(r, tuple):
            data, code = r
        else:
            data, code = r, 200
        return Response(json.dumps(data, cls=ArgonathJSONEncoder), status=code, mimetype='application/json')
    return _
