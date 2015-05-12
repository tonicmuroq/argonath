# coding: utf-8

from flask import url_for, redirect, Blueprint

bp = Blueprint('index', __name__, url_prefix='/')

@bp.route('/')
def index():
    return redirect(url_for('record.list_all_records'))
