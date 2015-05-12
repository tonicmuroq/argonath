# coding: utf-8

from functools import wraps
from flask import g, redirect

from argonath.ext import openid2

def need_login(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            return redirect(openid2.login_url)
        return f(*args, **kwargs)
    return _

def paginator_kwargs(kw):
    d = kw.copy()
    d.pop('start', None)
    d.pop('limit', None)
    return d
