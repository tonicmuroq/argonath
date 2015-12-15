import os

bind = '0.0.0.0:%s' % os.getenv('SERVER_PORT', '5000')
graceful_timeout = 3600
timeout = 3600
max_requests = 120
workers = 2
log_level = 'info'
debug = False
accesslog = '-'
access_log_format = ('%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" '
                     '"%(a)s" %(D)s %({X-Docker-Size}o)s')
