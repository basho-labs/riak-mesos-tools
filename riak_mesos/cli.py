#! /usr/bin/env python

#
#    Copyright (C) 2015 Basho Technologies, Inc.
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

# TODO: Add "wait for" commands to make command chaining and testing easier

import json
import os
import sys
import time
from sys import platform as _platform

import requests


def usage():
    print('Command line utility for the Riak Mesos Framework / DCOS Service.')
    print('This utility provides tools for modifying and accessing your Riak')
    print('on Mesos installation.')
    print('')
    print('Usage: riak-mesos <subcommands> [options]')
    print('')
    print('Subcommands: ')
    print('    config')
    print('    framework config')
    print('    framework install')
    print('    framework wait-for-service')
    print('    framework clean-metadata')
    print('    framework teardown')
    print('    framework uninstall')
    print('    framework endpoints')
    print('    cluster config [--file]')
    print('    cluster config advanced [--file]')
    print('    cluster list [--json]')
    print('    cluster create')
    print('    cluster wait-for-service')
    print('    cluster restart')
    print('    cluster destroy')
    print('    node info --node <name>')
    print('    node aae-status --node <name>')
    print('    node status --node <name>')
    print('    node ringready --node <name>')
    print('    node transfers --node <name>')
    print('    node bucket-type create --node <name> --bucket-type <name>')
    print('                            --props "<json>"')
    print('    node bucket-type list --node <name>')
    print('    node list [--json]')
    print('    node remove --node <name>')
    print('    node add [--nodes <number>]')
    print('    node wait-for-service [--node <name>]')
    print('    proxy config')
    print('    proxy install')
    print('    proxy uninstall')
    print('    proxy endpoints')
    print('    proxy wait-for-service')
    print('')
    print('Options (available on most commands): ')
    print('    --config <json-file> (/etc/riak-mesos/config.json)')
    print('    --cluster <cluster-name> (default)')
    print('    --debug')
    print('    --help')
    print('    --info')
    print('    --version')
    print('')

HELP_DICT = {
    'config': ('Displays configuration'),
    'framework': ('Displays configration for riak marathon app'),
    'framework uninstall':
    ('Removes the Riak Mesos Framework application from Marathon'),
    'framework teardown':
    ('Issues a teardown command for each of the matching frameworkIds to the Mesos master'),
    'framework clean-metadata':
    ('Deletes all metadata for the selected Riak Mesos Framework instance'),
    'proxy':
    ('Generates a marathon json config using --zookeeper (default is '
     'leader.mesos:2181) and --cluster (default is default).'),
    'proxy install':
    ('Installs a riak-mesos-director marathon app on the public Mesos node '
     'using --zookeeper (default is leader.mesos:2181) and --cluster (default '
     'is default).'),
    'proxy wait-for-service': ('Waits 20 seconds or until proxy is running'),
    'proxy uninstall': ('Uninstalls the riak-mesos-director marathon app.'),
    'proxy endpoints':
    ('Lists the endpoints exposed by a riak-mesos-director marathon app '
     '--public-dns (default is {{public-dns}}).'),
    'framework install': ('Retrieves a list of cluster names'),
    'framework wait-for-service': ('Waits 60 seconds or until Framework is running'),
    'framework endpoints': ('Retrieves useful endpoints for the framework'),
    'cluster config':
    ('Gets or sets the riak.conf configuration for a cluster, specify cluster '
     'id with --cluster and config file location with --file'),
    'cluster config advanced':
    ('Gets or sets the advanced.config configuration for a cluster, specify '
     'cluster id with --cluster and config file location with --file'),
    'cluster': ('Retrieves a list of cluster names'),
    'cluster create':
    ('Creates a new cluster. Specify the name with --cluster (default is '
     'default).'),
    'cluster wait-for-service':
    ('Iterates over all nodes in cluster and executes node wait-for-service.'),
    'cluster restart':
    ('Performs a rolling restart on a cluster. Specify the name with '
     '--cluster (default is default).'),
    'cluster destroy':
    ('Destroys a cluster. Specify the name with --cluster (default is '
     'default).'),
    'node':
    ('Retrieves a list of node ids for a given --cluster (default is '
     'default).'),
    'node info':
    ('Retrieves a list of node ids for a given --cluster (default is '
     'default).'),
    'node add':
    ('Adds one or more (using --nodes) nodes to a --cluster (default is '
     'default).'),
    'node wait-for-service': ('Waits 20 seconds or until node is running'),
    'node remove':
    ('Removes a node from the cluster, specify node id with --node'),
    'node aae-status':
    ('Gets the active anti entropy status for a node, specify node id with '
     '--node'),
    'node status':
    ('Gets the member-status of a node, specify node id with --node'),
    'node ringready':
    ('Gets the ringready value for a node, specify node id with --node'),
    'node transfers':
    ('Gets the transfers status for a node, specify node id with --node'),
    'node bucket-type create':
    ('Creates and activates a bucket type on a node, specify node id with '
     '--node'),
    'node bucket-type list':
    ('Gets the bucket type list from a node, specify node id with --node')
}


def help_dict():
    help = HELP_DICT
    help['framework config'] = help['framework']
    help['proxy config'] = help['proxy']
    help['cluster list'] = help['cluster']
    help['node list'] = help['node']
    return help


def help(cmd):
    return help_dict().get(cmd, False)


# Util
def is_dcos():
    if len(sys.argv) >= 2:
        return sys.argv[1] == 'riak'
    return False


class CliError(Exception):
    pass


class CaseException(Exception):
    pass


class case_selector(CaseException):
    def __init__(self, value):
        CaseException.__init__(self, value)


def switch(variable):
    raise case_selector(variable)


def case(value):
    exclass, exobj, tb = sys.exc_info()
    if exclass is case_selector and exobj.args[0] == value:
        return exclass
    return None


def multicase(*values):
    exclass, exobj, tb = sys.exc_info()
    if exclass is case_selector and exobj.args[0] in values:
        return exclass
    return None


def _to_exception(response):
    if response.status_code == 400:
        msg = 'Error on request [{0} {1}]: HTTP {2}: {3}'.format(
            response.request.method,
            response.request.url,
            response.status_code,
            response.reason)
        try:
            json_msg = response.json()
            msg += ':\n' + json.dumps(json_msg,
                                      indent=2,
                                      sort_keys=True,
                                      separators=(',', ': '))
        except ValueError:
            pass
        return Exception(msg)
    elif response.status_code == 409:
        return Exception(
            'App or group is locked by one or more deployments. '
            'Override with --force.')
    try:
        response_json = response.json()
    except Exception as ex:
        return ex
    message = response_json.get('message')
    if message is None:
        errs = response_json.get('errors')
        if errs is None:
            return Exception('Marathon likely misconfigured.')

        msg = '\n'.join(error['error'] for error in errs)
        return Exception('Marathon likely misconfigured.')
    return Exception('Error: {}'.format(message))


def _http_req(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except requests.exceptions.ConnectionError as e:
        raise e
    except requests.exceptions.RequestException as e:
        raise _to_exception(e.response)


# Config
class Config(object):
    def __init__(self, override_file=None):
        self._config = self.default_framework_config()
        if override_file is not None:
            with open(override_file) as data_file:
                data = json.load(data_file)
                self._merge(data)

    def zktool_command(self, command, path):
        tool = ''
        command = ''
        if _platform == 'linux' or _platform == 'linux2':
            tool = os.path.dirname(__file__) + '/' + 'zktool_linux_amd64'
        elif _platform == 'darwin':
            tool = os.path.dirname(__file__) + '/' + 'zktool_darwin_amd64'
        else:
            return False
        if command == 'get':
            args = tool + ' -zk=' + self.get('zk') + ' -name=' + path
            args += ' -command=zk-get-data'
            data = os.popen(args).read()
            if data.strip() == 'zk: node does not exist':
                return False
            elif data.strip() == 'zk: could not connect to a server':
                return False
            return data
        elif command == 'delete':
            args = tool + ' -zk=' + self.get('zk') + ' -name=' + path
            args += ' -command=zk-delete'
            output = os.popen(args).read()
            output += os.popen(args).read()
            output += os.popen(args).read()
            return output
        else:
            return False

    def kazoo_command(self, command, path):
        from kazoo.client import KazooClient
        zk = KazooClient(hosts=self.get('zk'))
        zk.start()
        node = path
        if command == 'get':
            data, stat = zk.get(node)
            return data.decode("utf-8")
        elif command == 'delete':
            zk.delete('/riak', recursive=True)
            return 'Successfully deleted ' + path
        else:
            return False
        zk.stop()

    def zk_command(self, command, path):
        result = ''
        if os.path.isfile(os.path.dirname(__file__) + '/zktool_linux_amd64'):
            result = self.zktool_command(command, path)
        if result:
            return result
        return self.kazoo_command(command, path)

    def zk_api_url(self):
        path = '/riak/frameworks/' + self.get('framework-name') + '/uri'
        url = self.zk_command('get', path)
        if url:
            return url.strip() + '/'
        return False

    def marathon_api_url(self):
        try:
            client = create_client(self.get_any('marathon', 'url'))
            tasks = client.get_tasks(self.get('framework-name'))
            if len(tasks) != 0:
                host = tasks[0]['host']
                port = tasks[0]['ports'][0]
                return 'http://' + host + ':' + str(port) + '/'
            return False
        except:
            return False

    def dcos_api_url(self):
        if not is_dcos():
            return False
        try:
            from dcos import util
            framework = self.get('framework-name')
            client = create_client(self.get_any('marathon', 'url'))
            tasks = client.get_tasks(self.get('framework-name'))
            if len(tasks) == 0:
                usage()
                raise CliError('Riak Mesos Framework is not running.')
            service_url = util.get_config().get('core.dcos_url').rstrip('/')
            service_url += '/service/' + framework + '/'
            r = requests.get(service_url + 'healthcheck')
            if r.status_code == 200:
                return service_url
            return False
        except:
            return False

    def api_url(self):
        try:
            service_url = self.dcos_api_url()
            if service_url:
                return service_url
            service_url = self.marathon_api_url()
            if service_url:
                return service_url
            service_url = self.zk_api_url()
            if service_url:
                return service_url
            error = 'Unable to connect to DCOS Server, Marathon, or Zookeeper.'
            raise CliError(error)
        except Exception as e:
            raise CliError('Unable to find api url: ' + e.message)

    def default_framework_config(self):
        download_base = 'http://riak-tools.s3.amazonaws.com'
        download_base += '/riak-mesos/ubuntu/'
        riak_pkg = 'riak_mesos_linux_amd64_0.3.0.tar.gz'
        director_pkg = 'riak_mesos_director_linux_amd64_0.3.0.tar.gz'
        riak_url = download_base + riak_pkg
        director_url = download_base + director_pkg
        return {
            'riak': {
                'master': 'zk://leader.mesos:2181/mesos',
                'zk': 'leader.mesos:2181',
                'ip': '',
                'hostname': 'riak.mesos',
                'log': '',
                'user': 'root',
                'framework-name': 'riak',
                'role': 'riak',
                'url': riak_url,
                'auth-provider': '',
                'auth-principal': 'riak',
                'auth-secret-file': '',
                'instances': 1,
                'cpus': 0.5,
                'mem': 2048,
                'node': {
                    'cpus': 1.0,
                    'mem': 8000,
                    'disk': 20000
                },
                'flags': '-use_reservations',
                'super-chroot': 'true',
                'healthcheck-grace-period-seconds': 300,
                'healthcheck-interval-seconds': 60,
                'healthcheck-timeout-seconds': 20,
                'healthcheck-max-consecutive-failures': 5
            },
            'director': {
                'url': director_url,
                'cmd': './director/bin/ermf-director',
                'use-public': False
            },
            'marathon': {
                'url': 'http://marathon.mesos:8080'
            }
        }

    def _fw_arg(self, name, var_name):
        if self.get(var_name) != '':
            return ' -' + name + '=' + self.get(var_name)
        return ''

    def _fw_arg_val(self, name, val):
        if val != '':
            return ' -' + name + '=' + str(val)
        return ''

    def framework_marathon_json(self):
        cmd = 'riak_mesos_framework/framework_linux_amd64'
        cmd += self._fw_arg('master', 'master')
        cmd += self._fw_arg('zk', 'zk')
        cmd += self._fw_arg('name', 'framework-name')
        cmd += self._fw_arg('user', 'user')
        cmd += self._fw_arg('ip', 'ip')
        cmd += self._fw_arg('hostname', 'hostname')
        cmd += self._fw_arg('log', 'log')
        cmd += self._fw_arg('role', 'role')
        cmd += self._fw_arg('mesos_authentication_provider', 'auth-provider')
        cmd += self._fw_arg('mesos_authentication_principal', 'auth-principal')
        cmd += self._fw_arg('mesos_authentication_secret_file', 'auth-secret-file')
        cmd += self._fw_arg_val('node_cpus', self.get('node', 'cpus'))
        cmd += self._fw_arg_val('node_mem', self.get('node', 'mem'))
        cmd += self._fw_arg_val('node_disk', self.get('node', 'disk'))
        cmd += ' ' + self.get('flags') if self.get('flags') != '' else ''
        healthcheck = {
            'path': '/healthcheck',
            'portIndex': 0,
            'protocol': 'HTTP',
            'gracePeriodSeconds':
            self.get('healthcheck-grace-period-seconds'),
            'intervalSeconds':
            self.get('healthcheck-interval-seconds'),
            'timeoutSeconds':
            self.get('healthcheck-timeout-seconds'),
            'maxConsecutiveFailures':
            self.get('healthcheck-max-consecutive-failures'),
            'ignoreHttp1xx': False
        }
        return {
            'id': self.get('framework-name'),
            'instances': self.get('instances'),
            'cpus': self.get('cpus'),
            'mem': self.get('mem'),
            'ports': [0, 0],
            'uris': [self.get('url')],
            'env': {'USE_SUPER_CHROOT': self.get('super-chroot')},
            'cmd': cmd,
            'healthChecks': [healthcheck]
        }

    def framework_marathon_string(self):
        return json.dumps(self.framework_marathon_json())

    def director_marathon_json(self, cluster):
        director_marathon_conf = {
            'id': '/riak-director',
            'cmd': self.get_any('director', 'cmd'),
            'cpus': 0.5,
            'mem': 500.0,
            'ports': [0, 0, 0, 0],
            'instances': 1,
            'env': {
                'USE_SUPER_CHROOT': self.get('super-chroot'),
                'DIRECTOR_ZK': self.get('zk'),
                'DIRECTOR_FRAMEWORK': self.get('framework-name'),
                'DIRECTOR_CLUSTER': cluster
            },
            'uris': [self.get_any('director', 'url')],
            'healthChecks': [
                {
                    'protocol': 'HTTP',
                    'path': '/health',
                    'gracePeriodSeconds': 3,
                    'intervalSeconds': 10,
                    'portIndex': 2,
                    'timeoutSeconds': 10,
                    'maxConsecutiveFailures': 3
                }
            ]
        }
        if self.get_any('director', 'use-public'):
            director_marathon_conf['acceptedResourceRoles'] = ['public']
        return director_marathon_conf

    def director_marathon_string(self, cluster):
        return json.dumps(self.director_marathon_json(cluster))

    def string(self):
        return json.dumps(self._config)

    def json(self):
        return self._config

    def get(self, key, subkey=None):
        return self.get_any('riak', key, subkey)

    def get_any(self, key, subkey1, subkey2=None):
        if subkey2 is not None and subkey2 is not None:
            return self._config[key][subkey1][subkey2]
        return self._config[key][subkey1]

    def _merge(self, override):
        tmp = self._config.copy()
        tmp.update(override)
        self._config = tmp


# Marathon
class Client(object):
    def __init__(self, marathon_url, timeout=6000):
        self._base_url = marathon_url
        self._timeout = timeout

    def normalize_app_id(self, app_id):
        return '/' + app_id.strip('/')

    def _create_url(self, path):
        return self._base_url + '/' + path

    def get_app(self, app_id):
        app_id = self.normalize_app_id(app_id)
        url = self._create_url('v2/apps{}'.format(app_id))
        response = _http_req(requests.get, url, timeout=self._timeout)
        return response.json()['app']

    def get_apps(self):
        url = self._create_url('v2/apps')
        response = _http_req(requests.get, url, timeout=self._timeout)
        return response.json()['apps']

    def add_app(self, app_resource):
        url = self._create_url('v2/apps')
        if hasattr(app_resource, 'read'):
            app_json = json.load(app_resource)
        else:
            app_json = app_resource
        response = _http_req(requests.post, url,
                             data=json.dumps(app_json),
                             timeout=self._timeout)
        return response.json()

    def scale_app(self, app_id, instances, force=None):
        app_id = self.normalize_app_id(app_id)
        if not force:
            params = None
        else:
            params = {'force': 'true'}
        url = self._create_url('v2/apps{}'.format(app_id))
        response = _http_req(requests.put,
                             url,
                             params=params,
                             data=json.dumps({'instances': int(instances)}),
                             timeout=self._timeout)
        deployment = response.json()['deploymentId']
        return deployment

    def stop_app(self, app_id, force=None):
        return self.scale_app(app_id, 0, force)

    def remove_app(self, app_id, force=None):
        app_id = self.normalize_app_id(app_id)
        if not force:
            params = None
        else:
            params = {'force': 'true'}
        url = self._create_url('v2/apps{}'.format(app_id))
        _http_req(requests.delete, url, params=params, timeout=self._timeout)

    def restart_app(self, app_id, force=None):
        app_id = self.normalize_app_id(app_id)
        if not force:
            params = None
        else:
            params = {'force': 'true'}
        url = self._create_url('v2/apps{}/restart'.format(app_id))
        response = _http_req(requests.post, url,
                             params=params,
                             timeout=self._timeout)
        return response.json()

    def get_tasks(self, app_id):
        url = self._create_url('v2/tasks')
        response = _http_req(requests.get, url, timeout=self._timeout)
        if app_id is not None:
            app_id = self.normalize_app_id(app_id)
            tasks = [
                task for task in response.json()['tasks']
                if app_id == task['appId']
            ]
        else:
            tasks = response.json()['tasks']
        return tasks

    def get_task(self, task_id):
        url = self._create_url('v2/tasks')
        response = _http_req(requests.get, url, timeout=self._timeout)
        task = next(
            (task for task in response.json()['tasks']
             if task_id == task['id']),
            None)
        return task


def create_client(marathon_url):
    if is_dcos():
        from dcos import marathon
        return marathon.create_client()
    else:
        return Client(marathon_url)


# Riak Mesos Framework
def pparr(description, json_str, failure):
    try:
        obj_arr = json.loads(json_str)
        print(description + '[' + ', '.join(obj_arr.keys()) + ']')
    except:
        print(description + failure)


def ppobj(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        print(description)
        if key == '':
            print(json.dumps(obj))
        else:
            print(json.dumps(obj[key]))
    except:
        print(description + failure)


def ppfact(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        if key == '':
            print(description + json.dumps(obj))
        else:
            print(description + json.dumps(obj[key]))
    except:
        print(description + failure)


def validate_arg(opt, arg, arg_type='string'):
    if arg.startswith('-'):
        raise CliError('Invalid argument for opt: ' + opt + ' [' + arg + '].')
    if arg_type == 'integer' and not arg.isdigit():
        raise CliError('Invalid integer for opt: ' + opt + ' [' + arg + '].')


def extract_flag(args, name):
    val = False
    if name in args:
        index = args.index(name)
        val = True
        del args[index]
    return [args, val]


def extract_option(args, name, default, arg_type='string'):
    val = default
    if name in args:
        index = args.index(name)
        if index+1 < len(args):
            val = args[index+1]
            validate_arg(name, val, arg_type)
            del args[index]
            del args[index]
        else:
            usage()
            print('')
            raise CliError('Not enough arguments for: ' + name)
    return [args, val]


def debug_request(debug_flag, r):
    debug(debug_flag, 'HTTP Status: ' + str(r.status_code))
    debug(debug_flag, 'HTTP Response Text: ' + r.text)


def debug(debug_flag, debug_string):
    if debug_flag:
        print('[DEBUG]' + debug_string + '[/DEBUG]')

def wait_for_url(url, seconds):
    if seconds == 0:
        return False
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return True
    except:
        pass
    time.sleep(1)
    return wait_for_url(url, seconds - 1)

def wait_for_framework(config, seconds):
    if seconds == 0:
        return False
    try:
        healthcheck_url = config.api_url() + 'healthcheck'
        if wait_for_url(healthcheck_url, 1):
            return True
    except:
        pass
    time.sleep(1)
    return wait_for_framework(config, seconds - 1)

def wait_for_node(config, node):
    if wait_for_framework(config, 60):
        service_url = config.api_url() + 'api/v1/'
        r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
        debug_request(debug_flag, r)
        node_json = json.loads(r.text)
        if wait_for_url('http://' + node_json[node]['Hostname'] + ':' +
                        str(node_json[node]['TaskData']['HTTPPort']), 20):
            print('Node ' + node + ' is ready.')
            return
        print('Node ' + node + ' did not respond in 20 seconds.')
        return
    print('Riak Mesos Framework did not respond within 60 seconds.')
    return


def run(args):
    def_conf = '/etc/riak-mesos/config.json'
    args, config_file = extract_option(args, '--config', def_conf)
    args, riak_file = extract_option(args, '--file', '')
    args, json_flag = extract_flag(args, '--json')
    args, help_flag = extract_flag(args, '--help')
    args, debug_flag = extract_flag(args, '--debug')
    args, cluster = extract_option(args, '--cluster', 'default')
    args, node = extract_option(args, '--node', '')
    args, bucket_type = extract_option(args, '--bucket-type', 'adhoc')
    args, props = extract_option(args, '--props', '')
    args, num_nodes = extract_option(args, '--nodes', '1', 'integer')
    num_nodes = int(num_nodes)
    cmd = ' '.join(args)
    debug(debug_flag, 'Cluster: ' + cluster)
    debug(debug_flag, 'Node: ' + node)
    debug(debug_flag, 'Nodes: ' + str(num_nodes))
    debug(debug_flag, 'Command: ' + cmd)

    cmd_desc = help(cmd)

    if help_flag and not cmd_desc:
        usage()
        return 0
    elif help_flag:
        print(cmd_desc)
        return 0

    if cmd == '':
        print('No commands executed')
        return
    elif cmd.startswith('-'):
        raise CliError('Unrecognized option: ' + cmd)
    elif not cmd_desc:
        raise CliError('Unrecognized command: ' + cmd)

    config = Config(None)
    if os.path.isfile(config_file):
        config = Config(config_file)

    try:
        switch(cmd)
    except case('config'):
        if json_flag:
            print(config.string())
        else:
            ppobj('Framework: ', config.string(), 'riak', '[]')
            ppobj('Director: ', config.string(), 'director', '[]')
            ppobj('Marathon: ', config.string(), 'marathon', '[]')
        return
    except multicase('framework config', 'framework'):
        obj = config.framework_marathon_string()
        if json_flag:
            ppobj('', obj, '', '{}')
        else:
            ppobj('Marathon Config: ', obj, '', '{}')
        return
    except case('framework uninstall'):
        print('Uninstalling framework...')
        fn = config.get('framework-name')
        client = create_client(config.get_any('marathon', 'url'))
        client.remove_app('/' + fn)
        print('Finished removing ' + '/' + fn + ' from marathon')
        return
    except case('framework clean-metadata'):
        fn = config.get('framework-name')
        print('\nRemoving zookeeper information\n')
        result = config.zk_command('delete', '/riak/frameworks/' + fn)
        if result:
            print(result)
        else:
            print("Unable to remove framework zookeeper data.")
        return
    except case('framework teardown'):
        r = requests.get('http://leader.mesos:5050/master/state.json')
        debug_request(debug_flag, r)
        if r.status_code != 200:
            print('Failed to get state.json from master.')
            return
        js = json.loads(r.text)
        for fw in js['frameworks']:
            if fw['name'] == config.get('framework-name'):
                r = requests.post('http://leader.mesos:5050/master/teardown', data='frameworkId='+js['id'])
                debug_request(debug_flag, r)
        print('Finished teardown.')
        return
    except multicase('proxy config', 'proxy'):
        print(config.director_marathon_string(cluster))
        return
    except case('proxy install'):
        director_json = config.director_marathon_json(cluster)
        client = create_client(config.get_any('marathon', 'url'))
        client.add_app(director_json)
        print('Finished adding ' + director_json['id'] + ' to marathon.')
        return
    except case('proxy uninstall'):
        client = create_client(config.get_any('marathon', 'url'))
        fn = config.get('framework-name')
        client.remove_app('/' + fn + '-director')
        print('Finished removing ' + '/' + fn + '-director' + ' from marathon')
        return
    except case('proxy endpoints'):
        client = create_client(config.get_any('marathon', 'url'))
        app = client.get_app(config.get('framework-name') + '-director')
        task = app['tasks'][0]
        ports = task['ports']
        hostname = task['host']
        print('Load Balanced Riak Cluster (HTTP)')
        print('    http://' + hostname + ':' + str(ports[0]))
        print('Load Balanced Riak Cluster (Protobuf)')
        print('    http://' + hostname + ':' + str(ports[1]))
        print('Riak Mesos Director API (HTTP)')
        print('    http://' + hostname + ':' + str(ports[2]))
        return
    except case('framework install'):
        framework_json = config.framework_marathon_json()
        client = create_client(config.get_any('marathon', 'url'))
        client.add_app(framework_json)
        wait_for_framework(config, 60)
        print('Finished adding ' + framework_json['id'] + ' to marathon')
        return
    except case('framework wait-for-service'):
        if wait_for_framework(config, 60):
            print('Riak Mesos Framework is ready.')
            return
        print('Riak Mesos Framework did not respond within 60 seconds.')
        return
    except case('node wait-for-service'):
        wait_for_node(config, node)
        return
    except case('cluster wait-for-service'):
        if wait_for_framework(config, 60):
            service_url = config.api_url() + 'api/v1/'
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            js = json.loads(r.text)
            for k in js.keys():
                wait_for_node(config, k)
            return
        print('Riak Mesos Framework did not respond within 60 seconds.')
        return
    except case('proxy wait-for-service'):
        if wait_for_framework(config, 60):
            client = create_client(config.get_any('marathon', 'url'))
            app = client.get_app(config.get('framework-name') + '-director')
            if(len(app['tasks'] == 0)):
                print("Proxy is not installed.")
                return
            task = app['tasks'][0]
            ports = task['ports']
            hostname = task['host']
            if wait_for_url('http://' + hostname + ':' + str(ports[0]), 20):
                print("Proxy is ready.")
                return
            print("Proxy did not respond in 20 seconds.")
            return
        print('Riak Mesos Framework did not respond within 60 seconds.')
        return
    except case('framework endpoints'):
        print('Not yet implemented.')
        # TODO impl
        return
    except:
        pass

    service_url = False
    try:
        service_url = config.api_url() + 'api/v1/'
        debug(debug_flag, 'Service URL: ' + service_url)
    except:
        raise CliError("Riak Mesos Framework is not running.")

    try:
        switch(cmd)
    except case('cluster config'):
        if riak_file == '':
            r = requests.get(service_url + 'clusters/' + cluster)
            debug_request(debug_flag, r)
            if r.status_code == 200:
                ppfact('riak.conf: ', r.text, 'RiakConfig',
                       'Error getting cluster.')
            else:
                print('Cluster not created.')
            return
        with open(riak_file) as data_file:
            r = requests.post(service_url + 'clusters/' + cluster + '/config',
                              data=data_file)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to set riak.conf, status_code: ' +
                      str(r.status_code))
            else:
                print('riak.conf updated')
    except case('cluster config advanced'):
        if riak_file == '':
            r = requests.get(service_url + 'clusters/' + cluster)
            debug_request(debug_flag, r)
            if r.status_code == 200:
                ppfact('advanced.config: ', r.text, 'AdvancedConfig',
                       'Error getting cluster.')
            else:
                print('Cluster not created.')
            return
        with open(riak_file) as data_file:
            r = requests.post(service_url + 'clusters/' + cluster +
                              '/advancedConfig', data=data_file)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to set advanced.config, status_code: ' +
                      str(r.status_code))
            else:
                print('advanced.config updated')
    except multicase('cluster list', 'cluster'):
        r = requests.get(service_url + 'clusters')
        debug_request(debug_flag, r)
        if r.status_code == 200:
            if json_flag:
                print(r.text)
            else:
                pparr('Clusters: ', r.text, '[]')
        else:
            print('No clusters created')
    except case('cluster create'):
        r = requests.post(service_url + 'clusters/' + cluster, data='')
        debug_request(debug_flag, r)
        if r.text == '' or r.status_code != 200:
            print('Cluster already exists.')
        else:
            ppfact('Added cluster: ', r.text, 'Name',
                   'Error creating cluster.')
    except case('cluster restart'):
        r = requests.post(service_url + 'clusters/' + cluster + '/restart',
                          data='')
        debug_request(debug_flag, r)
        if r.status_code == 404:
            print('Cluster does not exist.')
        elif r.status_code != 202:
            print('Failed to restart cluster, status code: ' +
                  str(r.status_code))
        else:
            print('Cluster restart initiated.')
    except case('cluster destroy'):
        r = requests.delete(service_url + 'clusters/' + cluster, data='')
        debug_request(debug_flag, r)
        if r.status_code != 202:
            print('Failed to destroy cluster, status_code: ' +
                  str(r.status_code))
        else:
            print('Destroyed cluster: ' + cluster)
    except multicase('node list', 'node'):
        r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
        debug_request(debug_flag, r)
        if json_flag:
            print(r.text)
        else:
            pparr('Nodes: ', r.text, '[]')
    except case('node info'):
        r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
        debug_request(debug_flag, r)
        node_json = json.loads(r.text)
        print('HTTP: http://' + node_json[node]['Hostname'] + ':' +
              str(node_json[node]['TaskData']['HTTPPort']))
        print('PB  : ' + node_json[node]['Hostname'] + ':' +
              str(node_json[node]['TaskData']['PBPort']))
        ppobj('Node: ', r.text, node, '{}')
    except case('node add'):
        for x in range(0, num_nodes):
            r = requests.post(service_url + 'clusters/' + cluster + '/nodes',
                              data='')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print(r.text)
            else:
                ppfact('New node: ' + config.get('framework-name') + '-' +
                       cluster + '-', r.text, 'SimpleId', 'Error adding node')
    except case('node remove'):
        if node == '':
            raise CliError('Node name must be specified')
        else:
            r = requests.delete(service_url + 'clusters/' + cluster +
                                '/nodes/' + node, data='')
            debug_request(debug_flag, r)
            if r.status_code != 202:
                print('Failed to remove node, status_code: ' +
                      str(r.status_code))
            else:
                print('Removed node')
    except case('node aae-status'):
        if node == '':
            raise CliError('Node name must be specified')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/aae')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get aae-status, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'aae-status', '{}')
    except case('node status'):
        if node == '':
            raise CliError('Node name must be specified')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/status')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get status, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'status', '{}')
    except case('node ringready'):
        if node == '':
            raise CliError('Node name must be specified')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/ringready')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get ringready, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'ringready', '{}')
    except case('node transfers'):
        if node == '':
            raise CliError('Node name must be specified')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/transfers')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get transfers, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'transfers', '{}')
    except case('node bucket-type create'):
        if node == '' or bucket_type == '' or props == '':
            raise CliError('Node name, bucket-type, props must be specified')
        else:
            r = requests.post(service_url + 'clusters/' + cluster + '/nodes/' +
                              node + '/types/' + bucket_type, data=props)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to create bucket-type, status_code: ' +
                      str(r.status_code))
                ppobj('', r.text, '', '{}')
            else:
                ppobj('', r.text, '', '{}')
    except case('node bucket-type list'):
        if node == '':
            raise CliError('Node name must be specified')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/types')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get bucket types, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'bucket_types', '{}')
    except CaseException as e:
        raise CliError('Unrecognized command: ' + cmd)
    except Exception as e:
        raise CliError('Error runing command: ' + e.message)
    return 0


def main():
    args = sys.argv[1:]
    if is_dcos():
        args = sys.argv[2:]
    if len(args) == 0:
        usage()
        return 0
    if '--info' in args:
        print('Start and manage Riak nodes')
        return 0
    if '--version' in args:
        print('Riak Mesos Framework Version 0.3.0')
        return 0
    if '--config-schema' in args:
        print('{}')
        return 0
    try:
        return_code = run(args)
        print('')
        return return_code
    except requests.exceptions.ConnectionError as e:
        print('ConnectionError: ' + str(e.message))
        return 1
    except CliError as e:
        print('CliError: ' + str(e.message))
        return 1
    except Exception as e:
        print('Exception: ' + str(e.message))
        return 1

if __name__ == '__main__':
    main()
