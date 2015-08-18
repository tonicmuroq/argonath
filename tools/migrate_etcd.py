#!/usr/bin/env python
# encoding: utf-8

import etcd
import json


def get_node(c, key):
    for node in c.read(key).leaves:
        if node.dir:
            for i in get_node(c, node.key):
                yield i
        else:
            yield node.key, node.value


if __name__=="__main__":
    source_host = raw_input("please enter source host and port. ")
    target_host = raw_input("please enter target host and port. ")
    src_host, src_ip = source_host.split(":")
    tgt_host, tgt_ip = target_host.split(":")
    source_etcd = etcd.Client(src_host, int(src_ip))
    target_etcd = etcd.Client(tgt_host, int(tgt_ip))

    nodes = dict(get_node(source_etcd, "/skydns/com"))
    for k, v in nodes.iteritems():
        host = json.loads(v)
        if host.get("default") is None:
            target_etcd.set(k, json.dumps({'default': [host]}))
