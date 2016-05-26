import json
import time
import requests

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
        assert c == 0
        assert e == b''
        js = json.loads(o.decode("utf-8").strip())
        assert len(js['nodes']) >= 2
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
    assert c == 0
    assert e == b''
    assert "riak-default-1 is ready" in o.strip()
    assert "riak-default-2 is ready" in o.strip()


def test_node_status():
    c, o, e = _fc(['node', 'status', '--node', 'riak-default-1'])
    js = json.loads(o.decode("utf-8").strip())
    assert js["status"]["valid"] == 2
    assert c == 0
    assert e == b''


def test_one_by_one():
    c, o, e = _fc(['node', 'info', '--node', 'riak-default-1'])
    js = json.loads(o.decode("utf-8").strip())
    host = js["riak-default-1"]["location"]["hostname"]
    port = js["riak-default-1"]["location"]["http_port"]
    put_data(host, port, 'test', 'test', 'test1')
    put_data(host, port, 'test', 'test', 'test2')
    put_data(host, port, 'test', 'test', 'test3')
    put_data(host, port, 'test', 'test', 'test4')
    put_data(host, port, 'test', 'test', 'test5')
    c, o, e = _fc(['node', 'add'])
    c, o, e = _fc(['node', 'wait-for-service', '--node', 'riak-default-3',
                   '--timeout', '600'])
    c, o, e = _fc(['node', 'transfers', 'wait-for-service', '--node',
                   'riak-default-3', '--timeout', '600'])
    assert "transfers complete" in o.strip()
    assert c == 0
    assert e == b''


def test_cluster_restart():
    c, o, e = _fc(['cluster', 'restart'])
    assert o.strip() == b'{"success":true}'
    assert c == 0
    assert e == b''
    time.sleep(15)
    c, o, e = _fc(['cluster', 'wait-for-service',
                   '--timeout', '600', '--nodes', '3'])
    assert c == 0
    assert e == b''
    assert "riak-default-1 is ready" in o.strip()
    assert "riak-default-2 is ready" in o.strip()
    assert "riak-default-3 is ready" in o.strip()


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


def put_data(host, port, bucket, key, value):
    requests.put('http://' + host + ":" + str(port) +
                 '/buckets/' + '/keys/' + 'test',
                 data=value)
