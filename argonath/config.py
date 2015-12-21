# coding: utf-8

import os

DEBUG = bool(os.getenv('DEBUG', ''))

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'argonath')

SQLALCHEMY_POOL_SIZE = 100
SQLALCHEMY_POOL_TIMEOUT = 10
SQLALCHEMY_POOL_RECYCLE = 2000

DEFAULT_NET = 'default'
ETCDS = os.getenv('ETCDS', 'localhost:4001')
SERVER_PORT = int(os.getenv('SERVER_PORT', '5000'))
OPENID_LOGIN_URL = os.getenv('OPENID_LOGIN_URL', '')
OPENID_PROFILE_URL = os.getenv('OPENID_PROFILE_URL', '')

try:
    from .local_config import *
except ImportError:
    pass

SQLALCHEMY_DATABASE_URI = 'mysql://{0}:{1}@{2}:{3}/{4}'.format(
    MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE,
)
