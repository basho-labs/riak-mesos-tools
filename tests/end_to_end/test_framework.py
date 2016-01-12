from common import exec_framework_command as _fc
import json
import requests
import time


def test_framework_install():
    c, o, e = _fc(['framework', 'install'])
    assert o == b'''Finished adding riak to marathon\n\n'''
    assert c == 0
    assert e == b''
    c, o, e = _fc(['framework', 'wait-for-service'])
    assert o == b'''Riak Mesos Framework is ready.\n\n'''
    assert c == 0
    assert e == b''


def test_cluster_create():
    c, o, e = _fc(['cluster', 'create'])
    expect1 = b'''Added cluster: "default"\n\n'''
    expect2 = b'''Cluster already exists\n\n'''
    assert o == expect1 or o == expect2
    assert c == 0
    assert e == b''


def test_cluster_list():
    c, o, e = _fc(['cluster', 'list', '--json'])
    js = json.loads(o)
    assert js["default"]["Name"] == b'default'
    assert c == 0
    assert e == b''


def test_node_list_add():
    c, o, e = _fc(['node', 'list'])
    if o == b'''Nodes: []\n\n''':
        c, o, e = _fc(['node', 'add'])
        assert o == b'New node: riak-default-1\n\n'
        assert c == 0
        assert e == b''
    else:
        c, o, e = _fc(['node', 'list'])
        assert o == b'''Nodes: [riak-default-1]\n\n'''
        assert c == 0
        assert e == b''
    c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-1'])
    assert o == b'''Node is ready.\n\n'''
    assert c == 0
    assert e == b''



def test_node_status():
    c, o, e = _fc(['node', 'list'])
