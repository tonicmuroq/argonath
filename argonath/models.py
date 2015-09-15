# coding: utf-8

import os
import etcd
import json
import datetime
import sqlalchemy.exc

from etcd import EtcdKeyError
from netaddr import IPNetwork, AddrFormatError
from sqlalchemy.ext.declarative import declared_attr

from argonath.ext import db
from argonath.config import ETCDS
from argonath.consts import DEFAULT_NET


def _get_host_port(s):
    h, p = s.split(':')
    return h, int(p)


_etcd_machines = [_get_host_port(host) for host in ETCDS.split(',')]
_etcd = etcd.Client(tuple(_etcd_machines), allow_reconnect=True)


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

    def __init__(self, name, domain):
        self.name = name
        self.domain = domain

    @classmethod
    def create(cls, user, name, domain, host_or_ip):
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
        return os.path.join('/skydns', '/'.join(reversed(self.domain.split('.'))))

    @property
    def skydns_data(self):
        try:
            r = _etcd.get(self.skydns_path)
            return json.loads(r.value)
        except (KeyError, EtcdKeyError):
            return {}

    @property
    def hosts(self):
        data = self.skydns_data
        if data:
            cidrs = data.keys()
            return_dict = {}
            for cidr in cidrs:
                return_dict[cidr] = [x['host'] for x in data[cidr]]
            return return_dict
        return data

    def add_host(self, cidr, host_or_ip):
        data = self.skydns_data
        if not data.get(cidr):
            data[cidr] = [{'host': host_or_ip}]
        elif host_or_ip not in [x['host'] for x in data[cidr]]:
            data[cidr].append({'host': host_or_ip})

        _etcd.set(self.skydns_path, json.dumps(data))

    def delete_host(self, cidr, host_or_ip):
        data = self.skydns_data
        if data.get(cidr):
            data[cidr] = [x for x in data[cidr] if x['host'] != host_or_ip]
        if not data[cidr]:
            del data[cidr]

        _etcd.set(self.skydns_path, json.dumps(data))

    def can_do(self, user):
        return user and (self.user_id == user.id or user.is_admin())

    def delete(self):
        _etcd.delete(self.skydns_path)

        db.session.delete(self)
        db.session.commit()

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
            self.name=name
            self.cidr=cidr
            db.session.add(self)
            db.session.commit()
            return self
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    def delete(self):
        db.session.delete(self)
        db.session.commit()
