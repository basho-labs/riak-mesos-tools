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

import logging
import os
import sys
import traceback
from os.path import expanduser

import click
from dcos import config as dcos_config
from dcos import errors as dcos_errors
from dcos import subcommand as dcos_subcommand
from dcos import http, marathon, mesos
from kazoo.client import KazooClient

from riak_mesos import constants
from riak_mesos.config import RiakMesosConfig

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


class RiakMesosDCOSStrategy(object):
    def __init__(self, ctx):
        self._master_url = None
        self._zk_url = None
        self._marathon_url = None
        self._framework_url = None
        self.ctx = ctx
        try:
            if self.ctx.framework is None:
                # Grab argv0, pump via dcos.subcommand.noun to get the fw name
                exe = sys.argv[0]
                self.framework = dcos_subcommand.noun(exe)
                if self.framework is None:
                    raise Exception("Unable to find Framework name")
                # Update the context with our newly found FW name
                self.ctx.framework = self.framework
            self.ctx.vlog('Attempting to create DCOSClient')
            dcos_client = mesos.DCOSClient()
            self.client = dcos_client
            dcos_url = self.client.get_dcos_url('')
            ssl_verify = dcos_config.get_config().get('core.ssl_verify')
            self.ctx.vlog('DCOS core.ssl_verify value = ' + str(ssl_verify))
            if ssl_verify is not None and (
                    not ssl_verify or ssl_verify == 'false'):
                self.ctx.vlog('Setting insecure_ssl to True')
                self.ctx.insecure_ssl = True
            if dcos_url is None:
                raise Exception("Unable to find DCOS server URL")
            dcos_url.rstrip('/')
            self.dcos_url = dcos_url
        except dcos_errors.DCOSException:
            raise Exception("DCOS is not configured properly")

    def framework_url(self):
        if self._framework_url is not None:
            return self._framework_url
        # TODO: get framework name from dcos?
        _framework_url = self.dcos_url + '/service/' + self.framework + '/'
        r = self.ctx.http_request('get',
                                  _framework_url + 'healthcheck',
                                  False)
        if r.status_code == 200:
            self._framework_url = _framework_url
            self.ctx.vlog("Setting framework URL to " +
                          self._framework_url)
            return self._framework_url
        raise CliError("Unable to to find framework URL")

    def marathon_url(self):
        if self._marathon_url is not None:
            return self._marathon_url
        _marathon = self.client.get_dcos_url('marathon/')
        r = self.ctx.http_request('get', _marathon + 'ping', False)
        if r.status_code == 200:
            self._marathon_url = _marathon
            self.ctx.vlog("Setting marathon URL to " +
                          self._marathon_url)
            return self._marathon_url
        raise CliError("Unable to to find marathon URL")

    def master_url(self):
        if self._master_url is not None:
            return self._master_url
        _mesos = self.client.master_url('')
        r = self.ctx.http_request('get', _mesos, False)
        if r.status_code == 200:
            self._master_url = _mesos
            self.ctx.vlog("Setting master URL to " +
                          self._master_url)
            return self._master_url
        raise CliError("Unable to to find master URL")

    def zk_url(self):
        if self._zk_url is not None:
            return self._zk_url
        _zk = 'leader.mesos:2181'
        # TODO: Get from dcos, and verify?
        self._zk_url = _zk
        self.ctx.vlog("Setting zookeeper URL to " +
                      self._zk_url)
        return self._zk_url


class RiakMesosClient(object):
    def __init__(self, ctx, _strategy=None):
        self._master_url = None
        self._zk_url = None
        self._marathon_url = None
        self._framework_url = None
        self.ctx = ctx

        if _strategy is not None:
            strategy = _strategy(ctx)
            if strategy.framework_url is not None:
                self.framework_url = strategy.framework_url
            if strategy.master_url is not None:
                self.master_url = strategy.master_url
            if strategy.zk_url is not None:
                self.zk_url = strategy.zk_url
            if strategy.marathon_url is not None:
                self.marathon_url = strategy.marathon_url
        else:
            self.ctx.vlog("Defaulting to configuration based URLs")

    def framework_url(self):
        if self._framework_url is not None:
            return self._framework_url
        _framework_url = self.ctx.config.get('framework-url')
        if _framework_url != '':
            _framework_url.rstrip('/')
            _framework_url = 'http://' + _framework_url + '/'
            r = self.ctx.http_request('get',
                                      _framework_url + 'healthcheck',
                                      False)
            if r.status_code == 200:
                self._framework_url = _framework_url
                self.ctx.vlog("Setting framework URL to " +
                              self._framework_url)
                return self._framework_url
        return self.marathon_framework_url()

    def marathon_framework_url(self):
        client = self.ctx.marathon_client()
        tasks = client.get_tasks(self.ctx.framework)
        for task in tasks:
            if task['state'] != "TASK_RUNNING":
                continue
            host = task['host']
            port = task['ports'][0]
            _framework_url = 'http://' + host + ':' + str(port) + '/'
            r = self.ctx.http_request('get',
                                      _framework_url + 'healthcheck',
                                      False)
            if r.status_code == 200:
                self._framework_url = _framework_url
                self.ctx.vlog("Setting framework URL to " +
                              self._framework_url)
                return self._framework_url
        raise CliError("Unable to to find framework URL")

    def marathon_url(self):
        if self._marathon_url is not None:
            return self._marathon_url
        _marathon = self.ctx.config.get('marathon')
        if _marathon == '':
            _marathon = 'marathon.mesos:8080'
        _marathon = 'http://' + _marathon + '/'
        r = self.ctx.http_request('get',
                                  _marathon + 'ping', False)
        if r.status_code == 200:
            self._marathon_url = _marathon
            self.ctx.vlog("Setting marathon URL to " +
                          self._marathon_url)
            return self._marathon_url
        raise CliError("Unable to to find marathon URL")

    def master_url(self):
        if self._master_url is not None:
            return self._master_url
        _master = self.ctx.config.get('master')
        if _master == '':
            _master = 'leader.mesos:5050'
        _master = 'http://' + _master + '/'
        r = self.ctx.http_request('get', _master, False)
        if r.status_code == 200:
            self._master_url = _master
            self.ctx.vlog("Setting master URL to " +
                          self._master_url)
            return self._master_url
        raise CliError("Unable to to find master URL")

    def zk_url(self):
        if self._zk_url is not None:
            return self._zk_url
        _zk = self.ctx.config.get('zk')
        if _zk != '':
            self._zk_url = _zk
            self.ctx.vlog("Setting zookeeper URL to " +
                          self._zk_url)
            return self._zk_url
        raise CliError("Unable to to find zk URL")


class Context(object):

    def __init__(self):
        # Flags
        self.verbose = False
        self.debug = False
        self.insecure_ssl = False
        self.json = False
        self.flags_set = False
        self.attach = False
        # Paths
        self.home = os.getcwd()
        self.config_file = None
        # JSON Config (optional for dcos)
        self.config = None
        # Conditional options
        self.framework = None
        self.cluster = 'default'
        self.node = 'riak-default-1'
        self.timeout = 60
        # RiakMesosClient
        self.client = None

    def cli_error(self, message):
        raise CliError(message)

    def _init_flags(self, verbose, debug, info, version,
                    config_schema, json, insecure_ssl, **kwargs):
        # Exit immediately if any of these are found
        if self.flags_set:
            return
        args = sys.argv[1:]
        if info or '--info' in args:
            click.echo('Start and manage Riak nodes in Mesos.')
            exit(0)
        if version or '--version' in args:
            click.echo('Riak Mesos Framework Version ' + constants.version)
            exit(0)
        if config_schema or '--config-schema' in args:
            click.echo('{}')
            exit(0)
        # Process remaining flags for all future command invocations
        if self.verbose or '--verbose' in args or '-v' in args:
            self.verbose = True
        else:
            self.verbose = verbose
        if self.insecure_ssl or '--insecure-ssl' in args:
            self.insecure_ssl = True
        else:
            self.insecure_ssl = insecure_ssl
        self.json = True if self.json or '--json' in args else json
        self.debug = True if self.debug or '--debug' in args else debug
        self.attach = True if self.attach or '--attach' in args else False
        # Configure logging for 3rd party libs
        if self.debug:
            logging.basicConfig(level=0)
            self.verbose = True
        elif self.verbose:
            logging.basicConfig(level=20)
        else:
            logging.basicConfig(level=50)
        self.flags_set = True
        self.vlog("Insecure SSL Mode: " + str(self.insecure_ssl))
        self.vlog("Verbose Mode: " + str(self.verbose))
        self.vlog("Debug Mode: " + str(self.debug))
        self.vlog("JSON Mode: " + str(self.json))

    def init_args(self, home, config, framework, cluster, node, **kwargs):
        self._init_flags(**kwargs)

        if home is not None:
            self.home = home
        if self.config is None or config is not None:
            if config is not None:
                self.config_file = config
            else:
                usr_conf_file = self.home + '/.config/riak-mesos/config.json'
                sys_conf_file = '/etc/riak-mesos/config.json'
                usr_home = expanduser("~")
                usr_home_conf_file = \
                    usr_home + '/.config/riak-mesos/config.json'
                if os.path.isfile(usr_conf_file):
                    self.config_file = usr_conf_file
                elif os.path.isfile(usr_home_conf_file):
                    self.config_file = usr_home_conf_file
                elif os.path.isfile(sys_conf_file):
                    self.config_file = sys_conf_file
                else:
                    self.config_file = None
            if self.config_file is not None:
                self.vlog('Using config file: ' + self.config_file)
            else:
                self.vlog('Couldn\'t find config file')

            self.config = RiakMesosConfig(self.config_file)

        if cluster is not None:
            self.cluster = cluster
        if node is not None:
            self.node = node

        if framework is not None:
            self.framework = framework
        if self.framework is None:
            _framework = self.config.get('framework-name')
            if framework is None and _framework != '':
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

    def vlog_request(self, r):
        """Logs request info to stderr only if verbose is enabled."""
        if self.debug:
            self.vlog('HTTP URL: ' + r.url)
            self.vlog('HTTP Method: ' + r.request.method)
            self.vlog('HTTP Body: ' + str(r.request.body))
            self.vlog('HTTP Status: ' + str(r.status_code))
            self.vlog('HTTP Response Text: ' + r.text)

    def vtraceback(self):
        if self.verbose:
            traceback.print_exc()

    def _init_client(self):
        ctx = self
        if self.config_file is None:
            try:
                _client = RiakMesosClient(ctx, RiakMesosDCOSStrategy)
                self.client = _client
                return
            except Exception as e:
                self.vlog(e.message)
        _client = RiakMesosClient(ctx)
        self.client = _client
        return

    def get_framework_url(self):
        if self.client is None:
            self._init_client()
        return self.client.framework_url()

    def api_request(self, method, path, exit_on_failure=True, **kwargs):
        return self.framework_request(method, 'api/v1/' + path,
                                      exit_on_failure, **kwargs)

    def framework_request(self, method, path, exit_on_failure=True, **kwargs):
        if self.client is None:
            self._init_client()
        try:
            framework_url = self.client.framework_url()
            return self.http_request(method,
                                     framework_url + path,
                                     exit_on_failure,
                                     **kwargs)
        except Exception as e:
            if exit_on_failure:
                raise e
            else:
                self.vlog(e)
                return FailedRequest(0, method,
                                     'framework_url_not_available/' + path)

    def master_request(self, method, path, exit_on_failure=True, **kwargs):
        if self.client is None:
            self._init_client()
        try:
            master_url = self.client.master_url()
            return self.http_request(method, master_url + path,
                                     exit_on_failure, **kwargs)
        except Exception as e:
            if exit_on_failure:
                raise e
            else:
                self.vlog(e)
                return FailedRequest(0, method,
                                     'master_url_not_available/' + path)

    def node_request(self, method, node, path, exit_on_failure=True, **kwargs):
        return self.framework_request(method, 'riak/nodes/' + node + '/' +
                                      path, exit_on_failure, **kwargs)

    def marathon_client(self):
        if self.client is None:
            self._init_client()
        marathon_url = self.client.marathon_url()
        return marathon.Client(marathon_url)

    def zk_command(self, command, path):
        if self.client is None:
            self._init_client()
        zk_url = self.client.zk_url()
        try:
            zk = KazooClient(hosts=zk_url)
            zk.start()
            res = False
            if command == 'get':
                data, stat = zk.get(path)
                res = data.decode("utf-8")
            elif command == 'delete':
                zk.delete(path, recursive=True)
                res = 'Successfully deleted ' + path
            zk.stop()
            return res
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
    click.option('--framework',
                 help='Changes the framework instance to operate on.'),
    click.option('--cluster',
                 help='Changes the cluster to operate on.'),
    click.option('--node',
                 help='Changes the node to operate on.'),
    click.option('--json', is_flag=True,
                 help='Enables json output.'),
    click.option('--insecure-ssl', is_flag=True,
                 help='Turns SSL verification off on HTTP requests')
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

    def get_command(self, ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            if name in ['riak', 'riak-ts', 'riak-kv']:
                return cli
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
