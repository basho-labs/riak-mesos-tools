from common import exec_command


def test_version():
    returncode, stdout, stderr = exec_command(
        ['riak-mesos', '--version'])

    assert returncode == 0
    assert stdout == b"""Riak Mesos Framework Version 0.3.0
"""
    assert stderr == b''
