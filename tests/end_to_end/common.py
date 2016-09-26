import os
import subprocess


def exec_framework_command(cmd, env=None, stdin=None):
    base_cmd = os.environ.get('RIAK_MESOS_CMD', 'riak-mesos').split()
    cmd = base_cmd + cmd
    return exec_command(cmd, env, stdin)


def exec_command(cmd, env=None, stdin=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: list of str
    :param env: Environment variables
    :type env: dict of str to str
    :param stdin: File to use for stdin
    :type stdin: file
    :returns: A tuple with the returncode, stdout and stderr
    :rtype: (int, bytes, bytes)
    """

    print('CMD: {!r}'.format(cmd))

    process = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env)

    stdout, stderr = process.communicate()

    # We should always print the stdout and stderr
    print('STDOUT: {!r}'.format(stdout.decode('utf-8')))
    print('STDERR: {!r}'.format(stderr.decode('utf-8')))

    return (process.returncode, stdout, stderr)
