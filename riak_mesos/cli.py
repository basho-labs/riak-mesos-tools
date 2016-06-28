#! /usr/bin/env python

#
#    Copyright (C) 2016 Basho Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Riak Mesos Framework CLI"""

import click
import logging
import os
import sys
import traceback

from dcos import http, util, marathon
from riak_mesos.config import RiakMesosConfig
from kazoo.client import KazooClient
from riak_mesos import constants


CONTEXT_SETTINGS = dict(auto_envvar_prefix='RIAK_MESOS')


class SubFailedRequest(object):
    def __init__(self, method):
        self.method = method
        self.body = ''


class FailedRequest(object):
    def __init__(self, status, method, url, text=''):
        self.status_code = status
        self.url = url
        self.request = SubFailedRequest(method)
        self.text = text


class CliError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class Context(object):

    def __init__(self):
        self.verbose = False
        self.debug = None
        self.home = os.getcwd()
        self.config_file = None
        self.config = None
        self.insecure_ssl = False
        self.timeout = 60
        self.master_url = None
        self.zk_url = None
        self.marathon_url = None
        self.framework_url = None
        self.framework = 'riak'
        self.cluster = 'default'
        self.node = 'riak-default-1'
        self.json = False

    def init_args(self, verbose, debug, home, config, info, version,
                  config_schema, json, cluster, node, **kwargs):
        if info:
            click.echo('Start and manage Riak nodes in Mesos.')
            exit(0)
        if version:
            click.echo('Riak Mesos Framework Version ' + constants.version)
            exit(0)
        if config_schema:
            click.echo('{}')
            exit(0)

        self.verbose = verbose
        self.json = json

        if self.debug is None:
            self.debug = debug
            if self.debug:
                logging.basicConfig(level=0)
                self.verbose = True
            elif self.verbose:
                logging.basicConfig(level=20)
            else:
                logging.basicConfig(level=50)

        if home is not None:
            self.home = home
        if self.config is None or config is not None:
            if config is not None:
                self.config_file = config
            else:
                usr_conf_file = self.home + '/.config/riak-mesos/config.json'
                sys_conf_file = '/etc/riak-mesos/config.json'
                if os.path.isfile(usr_conf_file):
                    self.config_file = usr_conf_file
                elif os.path.isfile(sys_conf_file):
                    self.config_file = sys_conf_file
                else:
                    from os.path import expanduser
                    usr_home = expanduser("~")
                    usr_home_conf_file = \
                        usr_home + '/.config/riak-mesos/config.json'
                    if os.path.isfile(usr_home_conf_file):
                        self.config_file = usr_home_conf_file
                    else:
                        self.config_file = None
            self.config = RiakMesosConfig(self.config_file)

        if cluster is not None:
            self.cluster = cluster
        if node is not None:
            self.node = node

        _framework = self.config.get('framework-name')
        if _framework != '':
            self.framework = _framework

        if 'timeout' in kwargs and kwargs['timeout'] is not None:
            self.timeout = kwargs['timeout']

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def vlog_request(self, r, *args):
        """Logs request info to stderr only if verbose is enabled."""
        self.vlog('HTTP URL: ' + r.url)
        self.vlog('HTTP Method: ' + r.request.method)
        self.vlog('HTTP Body: ' + str(r.request.body))
        self.vlog('HTTP Status: ' + str(r.status_code))
        self.vlog('HTTP Response Text: ' + r.text)

    def vtraceback(self):
        if self.verbose:
            traceback.print_exc()

    def _init_master(self):
        dcos_url = util.get_config().get('core.dcos_url')
        dcos_url.rstrip('/')
        _dcos_mesos = dcos_url + '/service/mesos/'
        _cfg_master = self.config.get('master')
        r = self.http_request('get', _dcos_mesos, False)
        if r.status_code == 200:
            self.master_url = _dcos_mesos
            return
        if _cfg_master == '':
            _cfg_master = 'leader.mesos:5050'
        _cfg_master = 'http://' + _cfg_master + '/'
        r = self.http_request('get', _cfg_master, False)
        if r.status_code == 200:
            self.master_url = _cfg_master
            return
        self.log("Unable to find Mesos Url using DCOS or " +
                 "Configuration")
        exit(1)

    def master_request(self, method, path, exit_on_failure=True, **kwargs):
        if self.master_url is None:
            self._init_master()
        return self.http_request(method, self.master_url + path,
                                 exit_on_failure, **kwargs)

    def _init_api(self):
        dcos_url = util.get_config().get('core.dcos_url')
        dcos_url.rstrip('/')
        _dcos_framework_url = dcos_url + '/service/' + self.framework + '/'
        _cfg_framework_url = self.config.get('framework-url')
        r = self.http_request('get',
                              _dcos_framework_url + 'healthcheck', False)
        self.vlog_request(r)
        if r.status_code == 200:
            self.framework_url = _dcos_framework_url
            return
        if _cfg_framework_url != '':
            r = self.http_request('get',
                                  _cfg_framework_url + 'healthcheck', False)
            self.vlog_request(r)
            if r.status_code == 200:
                self.framework_url = _cfg_framework_url
                return
        client = self.marathon_client()
        tasks = client.get_tasks(self.framework)
        if len(tasks) != 0:
            host = tasks[0]['host']
            port = tasks[0]['ports'][0]
            self.framework_url = 'http://' + host + ':' + str(port) + '/'
            return
        self.log("Unable to find Framework API Url using DCOS, " +
                 "Configuration, or Marathon")
        exit(1)

    def api_request(self, method, path, exit_on_failure=True, **kwargs):
        if self.framework_url is None:
            self._init_api()
        return self.http_request(method,
                                 self.framework_url + "api/v1/" + path,
                                 exit_on_failure,
                                 **kwargs)

    def framework_request(self, method, path, exit_on_failure=True, **kwargs):
        if self.framework_url is None:
            self._init_api()
        return self.http_request(method,
                                 self.framework_url + path,
                                 exit_on_failure,
                                 **kwargs)

    def _init_marathon(self):
        dcos_url = util.get_config().get('core.dcos_url')
        dcos_url.rstrip('/')
        _dcos_marathon = dcos_url + '/service/marathon/'
        _cfg_marathon = self.config.get('marathon')
        r = self.http_request('get', _dcos_marathon + 'ping', False)
        if r.status_code == 200:
            self.marathon_url = _dcos_marathon
            return
        if _cfg_marathon == '':
            _cfg_marathon = 'marathon.mesos:8080'
        _cfg_marathon = 'http://' + _cfg_marathon + '/'
        r = self.http_request('get',
                              _cfg_marathon + 'ping', False)
        if r.status_code == 200:
            self.marathon_url = _cfg_marathon
            return
        self.log("Unable to find Marathon Url using DCOS or " +
                 "Configuration")
        exit(1)

    def marathon_client(self):
        if self.marathon_url is None:
            self._init_marathon()
        self.vlog("Using Marathon URL: " + self.marathon_url)
        return marathon.Client(self.marathon_url)

    def _init_zk(self):
        _cfg_zk = self.config.get('zk')
        if _cfg_zk != '':
            self.zk_url = _cfg_zk
            return
        self.zk_url = 'leader.mesos:2181'
        return

    def zk_command(self, command, path):
        if self.zk_url is None:
            self._init_zk()
        try:
            zk = KazooClient(hosts=self.zk_url)
            zk.start()
            if command == 'get':
                data, stat = zk.get(path)
                return data.decode("utf-8")
            elif command == 'delete':
                zk.delete(path, recursive=True)
                return 'Successfully deleted ' + path
            else:
                return False
            zk.stop()
        except Exception as e:
            self.vlog(e)
            return False

    def http_request(self, method, url, exit_on_failure=True, **kwargs):
        try:
            verify = True
            if self.insecure_ssl:
                verify = False
            r = http.request(method,
                             url,
                             verify=verify,
                             is_success=_default_is_success,
                             **kwargs)
            self.vlog_request(r)
            if r.status_code == 404:
                return FailedRequest(
                    404, method, url,
                    'Resource at ' + url + ' was not found (Status Code: 404)')
            return r
        except Exception as e:
            if exit_on_failure:
                raise e
            else:
                self.vlog(e)
                return FailedRequest(0, method, url)


def _default_is_success(status_code):
    return 200 <= status_code <= 404


cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          'commands'))
_common_options = [
    click.make_pass_decorator(Context, ensure=True),
    click.option('--home',
                 type=click.Path(exists=True, file_okay=False,
                                 resolve_path=True),
                 help='Changes the folder to operate on.'),
    click.option('--config',
                 type=click.Path(exists=True, file_okay=True,
                                 resolve_path=True),
                 help='Path to JSON configuration file.'),
    click.option('-v', '--verbose', is_flag=True,
                 help='Enables verbose mode.'),
    click.option('--debug', is_flag=True,
                 help='Enables very verbose / debug mode.'),
    click.option('--info', is_flag=True, help='Display information.'),
    click.option('--version', is_flag=True, help='Display version.'),
    click.option('--config-schema', is_flag=True,
                 help='Display config schema.'),
    click.option('--cluster',
                 help='Changes the cluster to operate on.'),
    click.option('--node',
                 help='Changes the node to operate on.'),
    click.option('--json', is_flag=True,
                 help='Enables json output.')
]


def pass_context(func):
    for option in reversed(_common_options):
        func = option(func)
    return func


class RiakMesosCLI(click.MultiCommand):

    def __init__(self, *args, **kwargs):
        click.MultiCommand.__init__(self, *args,
                                    invoke_without_command=True,
                                    no_args_is_help=True,
                                    **kwargs)

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name=""):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            mod = __import__('riak_mesos.commands.cmd_' + name,
                             None, None, ['cli'])
        except ImportError:
            return
        return mod.cli


@click.group(cls=RiakMesosCLI, context_settings=CONTEXT_SETTINGS)
@pass_context
def cli(ctx, **kwargs):
    """Command line utility for the Riak Mesos Framework / DCOS Service.
    This utility provides tools for modifying and accessing your Riak
    on Mesos installation."""
    ctx.init_args(**kwargs)


# class RiakMesosCli(object):
#     def __init__(self, cli_args):
#         args = {}

#         # TODO: when in dcos cli env, "~/.dcos/dcos.toml" will have the dcos
#         # service url which we can use to find marathon, master, and service
#         # urls.

#         def_conf_file = None
#         user_home = pwd.getpwuid(os.getuid()).pw_dir
#         sys_conf_file = '/etc/riak-mesos/config.json'
#         usr_conf_file = user_home + '/.config/riak-mesos/config.json'
#         lcl_conf_file = '.config/riak-mesos/config.json'
#         if os.path.isfile(lcl_conf_file):
#             def_conf_file = lcl_conf_file
#         elif os.path.isfile(usr_conf_file):
#             def_conf_file = usr_conf_file
#         elif os.path.isfile(sys_conf_file):
#             def_conf_file = sys_conf_file

#         cli_args, config_file = extract_option(cli_args, '--config',
#                                                def_conf_file)
#         cli_args, args['riak_file'] = extract_option(cli_args, '--file',
#                                                      '')
#         cli_args, args['lines'] = extract_option(cli_args, '--lines',
#                                                  '1000')
#         cli_args, args['force_flag'] = extract_flag(cli_args, '--force')
#         cli_args, args['json_flag'] = extract_flag(cli_args, '--json')
#         cli_args, args['verify_ssl_flag'] = extract_flag(cli_args,
#                                                          '--verify-ssl')
#         cli_args, args['help_flag'] = extract_flag(cli_args, '--help')
#         cli_args, args['debug_flag'] = extract_flag(cli_args, '--debug')
#         cli_args, args['cluster'] = extract_option(cli_args, '--cluster',
#                                                    'default')
#         cli_args, args['node'] = extract_option(cli_args, '--node', '')
#         cli_args, args['bucket_type'] = extract_option(cli_args,
#                                                        '--bucket-type',
#                                                        'default')
#         cli_args, args['props'] = extract_option(cli_args, '--props', '')
#         cli_args, timeout = extract_option(cli_args, '--timeout',
#                                            '60', 'integer')
#         args['timeout'] = int(timeout)
#         cli_args, num_nodes = extract_option(cli_args, '--nodes', '1',
#                                              'integer')
#         args['num_nodes'] = int(num_nodes)
#         self.cmd = ' '.join(cli_args)
#         util.debug(args['debug_flag'], 'Cluster: ' + args['cluster'])
#         util.debug(args['debug_flag'], 'Node: ' + args['node'])
#         util.debug(args['debug_flag'], 'Nodes: ' +
#                    str(args['num_nodes']))
#         util.debug(args['debug_flag'], 'Command: ' + self.cmd)

#         if config_file is None or not os.path.isfile(config_file):
#                 raise CliError('No config file found')

#         self.cfg = RiakMesosConfig(config_file, args)

#     def run(self):
#         cmd_desc = help(self.cmd)

#         if self.cfg.args['help_flag'] and not cmd_desc:
#             print(constants.usage)
#             return 0
#         elif self.cfg.args['help_flag']:
#             print(cmd_desc)
#             return 0

#         if self.cmd == '':
#             print('No commands executed')
#             return
#         elif self.cmd.startswith('-'):
#             raise CliError('Unrecognized option: ' + self.cmd)
#         elif not cmd_desc:
#             raise CliError('Unrecognized command: ' + self.cmd)

#         try:
#             command_func_str = self.cmd.replace(' ', '_')
#             command_func_str = command_func_str.replace('-', '_')
#             util.debug(self.cfg.args['debug_flag'], 'Args: ' +
#                        str(self.cfg.args))
#             util.debug(self.cfg.args['debug_flag'], 'Command Func: ' +
#                        command_func_str + '(cfg)')
#             command_func = getattr(commands, command_func_str)
#             command_func(self.cfg)
#         except AttributeError as e:
#                 print('CliError: Unrecognized command: ' + self.cmd)
#                 if self.cfg.args['debug_flag']:
#                         traceback.print_exc()
#                         raise e

#         return 0


# def main():
#     args = sys.argv[1:]
#     if len(sys.argv) >= 2 and sys.argv[1] == 'riak':
#         args = sys.argv[2:]
#     if len(args) == 0:
#         print(constants.usage)
#         return 0
#     if '--info' in args:
#         print('Start and manage Riak nodes')
#         return 0
#     if '--version' in args:
#         print('Riak Mesos Framework Version ' + constants.version)
#         return 0
#     if '--config-schema' in args:
#         print('{}')
#         return 0
#     debug = False
#     if '--debug' in args:
#         debug = True

#     try:
#         cli = RiakMesosCli(args)
#         return cli.run()
#     except CliError as e:
#         print('CliError: ' + str(e))
#         if debug:
#             traceback.print_exc()
#             raise e
#         return 1
#     except Exception as e:
#         print(e)
#         if debug:
#             traceback.print_exc()
#             raise e
#         return 1

# if __name__ == '__main__':
#     main()
