# coding: utf-8

import os

from flask.ext.sqlalchemy import SQLAlchemy
from .openid2_ext import OpenID2

db = SQLAlchemy()
openid2 = OpenID2(file_store_path=os.getenv('ERU_PERMDIR', ''))

__all__ = ['db', 'openid2', ]
