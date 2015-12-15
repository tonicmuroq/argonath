# coding: utf-8

import os
import etcd
import json
import requests
import datetime
import sqlalchemy.exc

from etcd import EtcdKeyError
from netaddr import IPNetwork, AddrFormatError
from sqlalchemy.ext.declarative import declared_attr

from argonath.ext import db
from argonath.config import ETCDS, DEFAULT_NET

def _parse_reversed_domain(domain):
    return os.path.join('/skydns', '/'.join(reversed(domain.split('.'))))

def _get_host_port(s):
    h, p = s.split(':')
    return h, int(p)

_etcd_machines = [_get_host_port(host) for host in ETCDS.split(',')]
_etcd = etcd.Client(tuple(_etcd_machines), allow_reconnect=True)

def health_check():
    rs = {}
    for nodename, nodeinfo in _etcd.members.iteritems():
        if not nodeinfo['clientURLs']:
            rs[nodename] = False
            continue
        try:
            url = nodeinfo['clientURLs'][0]
            r = requests.get(url + '/health', timeout=3)
            rs[nodename] = json.loads(r.content)['health']
        except Exception:
            rs[nodename] = False
    return rs

class Base(db.Model):

    __abstract__ = True

    @declared_attr
    def id(cls):
        return db.Column('id', db.Integer, primary_key=True, autoincrement=True)

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id == id).first()

    @classmethod
    def get_multi(cls, ids):
        return [cls.get(i) for i in ids]

    def to_dict(self):
        keys = [c.key for c in self.__table__.columns]
        return {k: getattr(self, k) for k in keys}

    def __repr__(self):
        attrs = ', '.join('{0}={1}'.format(k, v) for k, v in self.to_dict().iteritems())
        return '{0}({1})'.format(self.__class__.__name__, attrs)

class Record(Base):

    __tablename__ = 'record'
    name = db.Column(db.String(255), unique=True, nullable=False, default='')
    domain = db.Column(db.String(255), unique=True, nullable=False, default='')
    time = db.Column(db.DateTime, default=datetime.datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comments = db.Column(db.Text, default='{}')

    def __init__(self, name, domain):
        self.name = name
        self.domain = domain

    @classmethod
    def create(cls, user, name, domain, host_or_ip, comment=''):
        """目前只支持A记录和CNAME"""
        try:
            r = cls(name, domain)
            user.records.append(r)
            db.session.add(r)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None
        else:
            data = json.dumps({DEFAULT_NET: [{'host': host_or_ip}]})

            _etcd.set(r.skydns_path, data)
            r.set_comment(host_or_ip, comment)

            return r

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @classmethod
    def get_by_domain(cls, domain):
        return cls.query.filter(cls.domain == domain).first()

    @classmethod
    def list_records(cls, start=0, limit=20):
        """还会返回总数"""
        q = cls.query.order_by(cls.id.desc())
        total = q.count()
        q = q.offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all(), total

    @property
    def skydns_path(self):
        return _parse_reversed_domain(self.domain)

    @property
    def skydns_data(self):
        try:
            r = _etcd.get(self.skydns_path)
            if r.dir:
                r = _etcd.get(os.path.join(self.skydns_path, '.self'))
            return json.loads(r.value)
        except (KeyError, EtcdKeyError):
            return {}

    @property
    def hosts(self):
        data = self.skydns_data
        if not data:
            return data
        return dict([
            (cidr, [h['host'] for h in hosts]) for cidr, hosts in data.iteritems()
        ])

    def get_comments(self):
        return json.loads(self.comments)

    def set_comment(self, host_or_ip, comment=''):
        comments = self.get_comments()
        comments[host_or_ip] = comment
        self.comments = json.dumps(comments)
        db.session.add(self)
        db.session.commit()

    def delete_comment(self, host_or_ip):
        comments = self.get_comments()
        comments.pop(host_or_ip, None)
        self.comments = json.dumps(comments)
        db.session.add(self)
        db.session.commit()

    def _parse_data(self, data):
        return dict([
            (cidr, [{'host': h} for h in hosts]) for cidr, hosts in data.iteritems()
        ])

    def add_host(self, cidr, host_or_ip, comment=''):
        data = self.hosts
        if not data.get(cidr):
            data[cidr] = [host_or_ip, ]
        elif host_or_ip not in data[cidr]:
            data[cidr].append(host_or_ip)

        _etcd.set(self.skydns_path, json.dumps(self._parse_data(data)))
        self.set_comment(host_or_ip, comment)

    def delete_host(self, cidr, host_or_ip):
        data = self.hosts
        if not data[cidr]:
            del data[cidr]
        else:
            data[cidr] = [x for x in data[cidr] if x != host_or_ip]

        _etcd.set(self.skydns_path, json.dumps(self._parse_data(data)))
        self.delete_comment(host_or_ip)

    def can_do(self, user):
        return user and (self.user_id == user.id or user.is_admin())

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return
        else:
            _etcd.delete(self.skydns_path)

    def to_dict(self):
        d = super(Record, self).to_dict()
        d['host'] = self.hosts
        return d

class User(Base):

    __tablename__ = 'user'
    name = db.Column(db.String(255), index=True, nullable=False, default='')
    email = db.Column(db.String(255), unique=True, nullable=False, default='')
    token = db.Column(db.String(255), unique=True, nullable=False, default='')
    admin = db.Column(db.Boolean, default=False)
    records = db.relationship('Record', backref='user', lazy='dynamic')

    def __init__(self, name, email, token):
        self.name = name
        self.email = email
        self.token = token

    @classmethod
    def get_or_create(cls, name, email):
        from argonath.utils import random_string
        u = cls.get_by_email(email)
        if u:
            return u
        try:
            u = cls(name, email, random_string(20))
            db.session.add(u)
            db.session.commit()
            return u
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter(cls.email == email).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @classmethod
    def get_by_token(cls, token):
        return cls.query.filter(cls.token == token).first()

    @classmethod
    def list_users(cls, start=0, limit=20):
        return cls.query.offset(start).limit(limit).all()

    @classmethod
    def transfer(cls, source_user, target_user):
        target_user.records.extend(source_user.records)
        source_user.records.delete()
        db.session.add(target_user)
        db.session.add(source_user)
        db.session.commit()

    def list_records(self, start=0, limit=20):
        """还会返回总数"""
        q = self.records.order_by(Record.id.desc())
        total = q.count()
        q = q.offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all(), total

    def is_admin(self):
        """-_-!"""
        return self.admin

    def to_dict(self):
        d = super(User, self).to_dict()
        d.pop('token', None)
        d['is_admin'] = self.is_admin()
        return d

class CIDR(Base):
    __tablename__ = "cidr"
    name = db.Column(db.String(255), unique=True, nullable=False)
    cidr = db.Column(db.String(255), unique=True, nullable=False)
    time = db.Column(db.DateTime, default=datetime.datetime.now)

    def __init__(self, name, cidr):
        self.name = name
        self.cidr = cidr

    @classmethod
    def create(cls, name, cidr):
        try:
            net = IPNetwork(cidr)
        except AddrFormatError:
            return None

        try:
            c = cls(name, str(net))
            db.session.add(c)
            db.session.commit()
            return c
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @classmethod
    def list_cidrs(cls, start=0, limit=20):
        q = cls.query.order_by(cls.id.desc())
        return q[start:start+limit], q.count()

    def is_default(self):
        return self.name == DEFAULT_NET

    def edit(self, name, cidr):
        try:
            IPNetwork(cidr)
        except AddrFormatError:
            return None
        try:
            self.name = name
            self.cidr = cidr
            db.session.add(self)
            db.session.commit()
            return self
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Domain(Base):
    __tablename__ = "domain"

    domain = db.Column(db.String(255), unique=True, nullable=False)
    reversed_path = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, domain):
        self.domain = domain
        self.reversed_path = _parse_reversed_domain(domain)

    @classmethod
    def create(cls, domain):
        try:
            d = cls(domain)
            db.session.add(d)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None
        else:
            try:
                r = _etcd.read(d.reversed_path)
            except etcd.EtcdKeyNotFound:
                _etcd.write(d.reversed_path, None, dir=True)
                return d
            else:
                if r.dir:
                    return d
                #拿到之前的值
                v = r.value
                _etcd.delete(d.reversed_path)
                _etcd.write(os.path.join(d.reversed_path, '.self'), v)
                return d

    @classmethod
    def get_by_name(cls, domain):
        return cls.query.filter(cls.domain == domain).first()

    @classmethod
    def list_domains(cls, start=0, limit=20):
        q = cls.query.order_by(cls.id.desc())
        return q[start:start+limit], q.count()

    @classmethod
    def get_all(cls):
        return [item.domain for item in cls.query.all()]

    def edit(self, domain):
        try:
            self.domain = domain
            self.reversed_path = _parse_reversed_domain(domain)
            db.session.add(self)
            db.session.commit()
            return self
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
        else:
            try:
                r = _etcd.read(self.reversed_path)
                if r.dir:
                    _etcd.delete(self.reversed_path, recursive=True, dir=True)
                else:
                    _etcd.delete(self.reversed_path)
            except etcd.EtcdKeyNotFound:
                return True
            except Exception:
                return False
            else:
                return True

