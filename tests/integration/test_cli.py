from common import exec_command as _c
import json


def test_version():
    c, o, e = _c(['riak-mesos', '--version'])
    assert c == 0
    assert o == b'''Riak Mesos Framework Version 0.3.0\n'''
    assert e == b''


def test_help():
    c, o, e = _c(['riak-mesos'])
    assert c == 0
    assert e == b''
    c, o, e = _c(['riak-mesos', '--help'])
    assert c == 0
    assert e == b''
    c, o, e = _c(['riak-mesos', 'config', '--help'])
    assert c == 0
    assert e == b''
    assert o == b'''Displays configuration\n'''


def test_config():
    c, o, e = _c(['riak-mesos', 'config', '--json'])
    js = json.loads(o)
    assert js['director']['use-public'] is False
    assert c == 0
    assert e == b''


def test_framework_config():
    c, o, e = _c(['riak-mesos', 'framework', 'config', '--json'])
    js = json.loads(o)
    assert js['id'] == b'riak'
    assert c == 0
    assert e == b''
