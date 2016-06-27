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
import dcos
import json
import os
import sys
import traceback

from riak_mesos import util
from riak_mesos.config import RiakMesosConfig


CONTEXT_SETTINGS = dict(auto_envvar_prefix='RIAK_MESOS')


class Context(object):

    def __init__(self):
        self.verbose = False
        self.home = os.getcwd()
        self.config_file = None
        self.config = None
        self.insecure_ssl = False
        self.timeout = 60
        self.master_url = 'leader.mesos:5050'
        self.zk_url = 'leader.mesos:2181'
        self.marathon_url = 'marathon.mesos:8080'
        self.framework_url = None
        self.framework = 'riak'
        self.cluster = 'default'
        self.node = 'riak-default-1'

    def load_urls(self):
        dcos_url = dcos.util.get_config().get('core.dcos_url')
        dcos_url.rstrip('/')

        _dcos_marathon = dcos_url + '/service/marathon/'
        _dcos_mesos = dcos_url + '/service/mesos/'
        _dcos_framework_url = dcos_url + '/service/' + self.framework + '/'

        _cfg_marathon = self.config.get('marathon')
        _cfg_master = self.config.get('master')
        _cfg_zk = self.config.get('zk')
        _cfg_framework_url = self.config.get('framework-url')

        r = util.http_request('get', _dcos_framework_url + 'healthcheck')
        if r.status_code == 200:
            self.framework_url = _dcos_framework_url
        r = util.http_request('get', _dcos_marathon + 'ping')
        if r.status_code == 200:
            self.marathon_url = _dcos_marathon
        r = util.http_request('get', _dcos_mesos)
        if r.status_code == 200:
            self.master_url = _dcos_mesos

        if _cfg_marathon != '':
            self.marathon_url = _cfg_marathon
        if _cfg_master != '':
            self.master_url = _cfg_master
        if _cfg_zk != '':
            self.zk_url = _cfg_zk
        if _cfg_framework_url != '':
            self.framework_url = _cfg_framework_url

        client = util.marathon_client(ctx.marathon_url)
        tasks = client.get_tasks(ctx.framework)
        if len(tasks) != 0:
            host = tasks[0]['host']
            port = tasks[0]['ports'][0]
            return 'http://' + host + ':' + str(port) + '/'

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

    def api_url(self):
        scheduler_url = self.scheduler_url()
        return scheduler_url + "api/v1/"

    def scheduler_url(self):
        if self.framework_url is None:
            self.framework_url = find_framework_url(self)
        return self.framework_url


pass_context = click.make_pass_decorator(Context, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          'commands'))


class RiakMesosCLI(click.MultiCommand):

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            mod = __import__('riak_mesos.commands.cmd_' + name,
                             None, None, ['cli'])
        except ImportError:
            return
        return mod.cli


@click.command(cls=RiakMesosCLI, context_settings=CONTEXT_SETTINGS)
@click.option('--home', type=click.Path(exists=True, file_okay=False,
                                        resolve_path=True),
              help='Changes the folder to operate on.')
@click.option('--config', type=click.Path(exists=True, file_okay=True,
                                          resolve_path=True),
              help='Path to JSON configuration file.')
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode.')
@pass_context
def cli(ctx, verbose, home, config):
    """A complex command line interface."""
    ctx.verbose = verbose
    if home is not None:
        ctx.home = home
    if config is not None:
        ctx.config_file = config
    else:
        ctx.config_file = find_config(ctx.home)
    ctx.config = RiakMesosConfig(ctx.config_file)

    _framework = ctx.config.get('framework-name')
    if _framework != '':
        ctx.framework = _framework
    ctx.load_urls()


def find_config(home):
    usr_conf_file = home + '/.config/riak-mesos/config.json'
    sys_conf_file = '/etc/riak-mesos/config.json'
    if os.path.isfile(usr_conf_file):
        return usr_conf_file
    elif os.path.isfile(sys_conf_file):
        return sys_conf_file
    return None


def find_framework_url(ctx):
    try:
        service_url = marathon_api_url(ctx)
        if service_url:
            return service_url
        error = 'Unable to connect to DCOS Server, Marathon, or Zookeeper.'
        raise util.CliError(error)
    except Exception as e:
        raise util.CliError('Unable to find api url: ' + e.message)


def marathon_api_url(ctx):
    try:
        
        else:
            print("Task not running in Marathon")
        return False
    except:
        ctx.vtraceback()
        return False


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
