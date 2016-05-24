import json
import time

from common import exec_framework_command as _fc


def test_framework_install():
    c, o, e = _fc(['framework', 'install'])
    assert o.strip() == b'Finished adding riak to marathon.'
    assert c == 0
    assert e == b''
    c, o, e = _fc(['framework', 'wait-for-service', '--timeout', '600'])
    assert o.strip() == b'Riak Mesos Framework is ready.'
    assert c == 0
    assert e == b''


def test_cluster_create():
    c, o, e = _fc(['cluster', 'create'])
    expect1 = b'{"success":true}'
    expect2 = b'{"success":false,"error":"exists"}'
    assert o.strip() == expect1 or o.strip() == expect2
    assert c == 0
    assert e == b''


def test_cluster_list():
    c, o, e = _fc(['cluster', 'list', '--json'])
    js = json.loads(o.decode("utf-8").strip())
    assert js["clusters"][0] == 'default'
    assert c == 0
    assert e == b''


def test_node_list_add():
    c, o, e = _fc(['node', 'list'])
    if o == b'''{"nodes":[]}\n''':
        c, o, e = _fc(['node', 'add', '--nodes', '2'])
        assert o.strip() == b'''{"success":true}
{"success":true}'''
        assert c == 0
        assert e == b''
    else:
        c, o, e = _fc(['node', 'list'])
        expect1 = b'{"nodes":["riak-default-1","riak-default-2"]}'
        expect2 = b'{"nodes":["riak-default-2","riak-default-1"]}'
        assert o.strip() == expect1 or o.strip() == expect2
        assert c == 0
        assert e == b''
    c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-1',
                   '--timeout', '600'])
    assert c == 0
    assert e == ''
    c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-2',
                   '--timeout', '600'])
    assert c == 0
    assert e == ''
    c, o, e = _fc(['cluster', 'wait-for-service',
                   '--timeout', '600', '--nodes', '2'])
    expect1 = b'''Node riak-default-1 is ready.
Node riak-default-2 is ready.
Cluster default is ready.'''
    expect2 = b'''Node riak-default-2 is ready.
Node riak-default-1 is ready.
Cluster default is ready.'''
    assert o.strip() == expect1 or o.strip() == expect2
    assert c == 0
    assert e == b''


def test_node_status():
    c, o, e = _fc(['node', 'status', '--node', 'riak-default-1'])
    js = json.loads(o.decode("utf-8").strip())
    assert js["status"]["valid"] == 2
    assert c == 0
    assert e == b''


# def test_cluster_restart():
#     c, o, e = _fc(['cluster', 'restart'])
#     assert o.strip() == b'{"success":true}'
#     assert c == 0
#     assert e == b''
#     time.sleep(15)
#     c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-1'])
#     assert c == 0
#     assert e == ''
#     c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-2'])
#     assert c == 0
#     assert e == ''
#     c, o, e = _fc(['cluster', 'wait-for-service'])
#     expect1 = b'''Node riak-default-1 is ready.
# Node riak-default-2 is ready.'''
#     expect2 = b'''Node riak-default-2 is ready.
# Node riak-default-1 is ready.'''
#     assert o.strip() == expect1 or o.strip() == expect2
#     assert c == 0
#     assert e == b''


def test_uninstall():
    c, o, e = _fc(['cluster', 'destroy'])
    assert c == 0
    time.sleep(15)
    c, o, e = _fc(['framework', 'uninstall'])
    assert c == 0
    c, o, e = _fc(['framework', 'teardown'])
    assert c == 0
    c, o, e = _fc(['framework', 'clean-metadata'])
    assert c == 0
