from common import exec_framework_command as _fc


def test_framework_install():
    c, o, e = _fc(['framework', 'install'])
    assert o == b'''Finished adding riak to marathon\n\n'''
    assert c == 0
    assert e == b''


def test_cluster_create():
    c, o, e = _fc(['cluster', 'create'])
    assert o == b'''Finished adding riak to marathon\n\n'''
    assert c == 0
    assert e == b''
