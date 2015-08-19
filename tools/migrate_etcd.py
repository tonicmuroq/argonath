#!/usr/bin/env python
# encoding: utf-8

import etcd
import json
import sys


def get_node(c, key):
    for node in c.read(key, recursive=True).leaves:
        yield node.key, node.value

def create(addr):
    addr_host, addr_port = addr.split(":")
    return etcd.Client(addr_host, int(addr_port))

def main(src, dst):
    source_etcd = create(src)
    target_etcd = create(dst)

    nodes = dict(get_node(source_etcd, "/skydns/com/hunantv"))
    for k, v in nodes.iteritems():
        if not v or k == '.wildcards':
            continue
        host = json.loads(v)
        if host.get("default", None):
            continue
        target_etcd.set(k, json.dumps({'default': [host]}))

def check(src):
    c = create(src)
    r = c.read('/skydns/com/hunantv', recursive=True)
    for node in r.get_subtree():
        if node.dir:
            continue
        v = json.loads(node.value)
        if v.get('default'):
            continue
        print node.key, v

if __name__=="__main__":
    src = sys.argv[1]
    dst = sys.argv[2]
    print src, dst
    main(src, dst)
    check(dst)
