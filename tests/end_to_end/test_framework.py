import json

from common import exec_framework_command as _fc


def test_framework_install():
    c, o, e = _fc(['framework', 'install'])
    assert o.strip() == b'Finished adding riak to marathon.'
    assert c == 0
    assert e == b''
    c, o, e = _fc(['framework', 'wait-for-service'])
    assert o.strip() == b'Riak Mesos Framework is ready.'
    assert c == 0
    assert e == b''


def test_cluster_create():
    c, o, e = _fc(['cluster', 'create'])
    expect1 = b'Added cluster: "default"'
    expect2 = b'Cluster already exists.'
    assert o.strip() == expect1 or o.strip() == expect2
    assert c == 0
    assert e == b''


def test_cluster_list():
    c, o, e = _fc(['cluster', 'list', '--json'])
    js = json.loads(o.decode("utf-8").strip())
    assert js["default"]["Name"] == 'default'
    assert c == 0
    assert e == b''


def test_node_list_add():
    c, o, e = _fc(['node', 'list'])
    if o == b'''Nodes: []\n\n''':
        c, o, e = _fc(['node', 'add', '--nodes', '2'])
        assert o.strip() == b'''New node: riak-default-1
New node: riak-default-2'''
        assert c == 0
        assert e == b''
    else:
        c, o, e = _fc(['node', 'list'])
        assert o.strip() == b'Nodes: [riak-default-1]'
        assert c == 0
        assert e == b''
    c, o, e = _fc(['cluster', 'wait-for-service'])
    assert c == 0
    assert e == ''
    c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-1'])
    assert o.strip() == b'Node riak-default-1 is ready.'
    assert c == 0
    assert e == b''


def test_node_status():
    c, o, e = _fc(['node', 'list'])
