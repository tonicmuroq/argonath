# coding: utf-8

import sys
import os
sys.path.append(os.path.abspath('.'))

from argonath.app import create_app
from argonath.ext import db
from argonath.models import User, Record

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
