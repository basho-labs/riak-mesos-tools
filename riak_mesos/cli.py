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

from __future__ import print_function
import subprocess
import os
import sys
import requests
import json
from sys import platform as _platform

##########################################################
###################### Usage #############################
##########################################################

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
    print('    framework clean-metadata')
    print('    framework uninstall')
    print('    framework endpoints')
    print('    cluster config [--file]')
    print('    cluster config advanced [--file]')
    print('    cluster list [--json]')
    print('    cluster create')
    print('    cluster restart')
    print('    cluster destroy')
    print('    node info --node <name>')
    print('    node aae-status --node <name>')
    print('    node status --node <name>')
    print('    node ringready --node <name>')
    print('    node transfers --node <name>')
    print('    node bucket-type create --node <name> --bucket-type <name> --props "<json>"')
    print('    node bucket-type list --node <name>')
    print('    node list [--json]')
    print('    node remove --node <name>')
    print('    node add [--nodes <number>]')
    print('    proxy config')
    print('    proxy install')
    print('    proxy uninstall')
    print('    proxy endpoints')
    print('')
    print('Options (available on most commands): ')
    print('    --config <json-file>         Default: /etc/riak-mesos/config.json')
    print('    --cluster <cluster-name>     Default: default')
    print('    --debug')
    print('    --help')
    print('    --info')
    print('    --version')
    print('')

##########################################################
######################## Util ############################
##########################################################

def is_dcos():
    return sys.argv[1] == 'riak'

class case_selector(Exception):
   def __init__(self, value): # overridden to ensure we've got a value argument
      Exception.__init__(self, value)

def switch(variable):
   raise case_selector(variable)

def case(value):
   exclass, exobj, tb = sys.exc_info()
   if exclass is case_selector and exobj.args[0] == value: return exclass
   return None

def multicase(*values):
   exclass, exobj, tb = sys.exc_info()
   if exclass is case_selector and exobj.args[0] in values: return exclass
   return None

class CliError(Exception):
    pass

##########################################################
######################## Config ##########################
##########################################################

class Config(object):
    def __init__(self, override_file=None):
        self._config = self.default_framework_config()
        if override_file != None:
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
            data = os.popen(tool + ' -zk=' + self.get('zk') + ' -name=' + path + ' -command=zk-get-data').read()
            if data.strip() == 'zk: node does not exist':
                return False
            elif data.strip() == 'zk: could not connect to a server':
                return False
            return data
        elif command == 'delete':
            output = ''
            output += os.popen(tool + ' -zk=' + self.get('zk') + ' -name=' + path + ' -command=zk-delete').read()
            output += os.popen(tool + ' -zk=' + self.get('zk') + ' -name=' + path + ' -command=zk-delete').read()
            output += os.popen(tool + ' -zk=' + self.get('zk') + ' -name=' + path + ' -command=zk-delete').read()
            output += 'Successfully deleted ' + path
            return output
        else:
            return False

    def kazoo_command(self, command, path):
        from kazoo.client import KazooClient
        zk = KazooClient(hosts=self.get('zk'))
        zk.start()
        node=path
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
        if result: return result
        return self.kazoo_command(command, path)

    def zk_api_url(self):
        url = self.zk_command('get', '/riak/frameworks/' + self.get('framework-name') + '/uri')
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
                print('\nTry running the following to verify that ' + framework + ' is the name \nof your service instance:\n')
                print('    dcos service\n')
                raise CliError('Riak Mesos Framework is not running, try creating a dcos-riak.json with your correct framework name and run with --config dcos-riak.json')
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
            if service_url: return service_url
            service_url = self.marathon_api_url()
            if service_url: return service_url
            service_url = self.zk_api_url()
            if service_url: return service_url
            raise CliError('Unable to connect to DCOS Server, Marathon, or Zookeeper.')
        except Exception as e:
            raise CliError('Unable to find api url: ' + e.message)

    def default_framework_config(self):
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
                'url': 'http://riak-tools.s3.amazonaws.com/riak-mesos/ubuntu/riak_mesos_linux_amd64_0.3.0.tar.gz',
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
                'url': 'http://riak-tools.s3.amazonaws.com/riak-mesos/ubuntu/riak_mesos_director_linux_amd64_0.3.0.tar.gz',
                'cmd': './director/bin/ermf-director',
                'use-public': False
            },
            'marathon': {
                'url': 'http://marathon.mesos:8080'
            }
        }

    def framework_marathon_json(self):
        framework_cmd = 'riak_mesos_framework/framework_linux_amd64'
        framework_cmd += ' -master='+self.get('master')
        framework_cmd += ' -zk='+self.get('zk')
        framework_cmd += ' -name='+self.get('framework-name')
        framework_cmd += ' -user='+self.get('user')
        framework_cmd += ' -ip='+self.get('ip') if self.get('ip')!='' else ''
        framework_cmd += ' -hostname='+self.get('hostname') if self.get('hostname')!='' else ''
        framework_cmd += ' -log='+self.get('log') if self.get('log')!='' else ''
        framework_cmd += ' -role='+self.get('role') if self.get('role')!='' else ''
        framework_cmd += ' -mesos_authentication_provider='+self.get('auth-provider') if self.get('auth-provider')!='' else ''
        framework_cmd += ' -mesos_authentication_principal='+self.get('auth-principal') if self.get('auth-principal')!='' else ''
        framework_cmd += ' -mesos_authentication_secret_file='+self.get('auth-secret-file') if self.get('auth-secret-file')!='' else ''
        framework_cmd += ' -node_cpus='+str(self.get('node','cpus'))
        framework_cmd += ' -node_mem='+str(self.get('node','mem'))
        framework_cmd += ' -node_disk='+str(self.get('node','disk'))
        framework_cmd += ' '+self.get('flags') if self.get('flags')!='' else ''
        return {
          'id': self.get('framework-name'),
          'instances': self.get('instances'),
          'cpus': self.get('cpus'),
          'mem': self.get('mem'),
          'ports': [0, 0],
          'uris': [self.get('url')],
          'env': {'USE_SUPER_CHROOT': self.get('super-chroot')},
          'cmd': framework_cmd,
          'healthChecks': [
            {
              'path': '/healthcheck',
              'portIndex': 0,
              'protocol': 'HTTP',
              'gracePeriodSeconds': self.get('healthcheck-grace-period-seconds'),
              'intervalSeconds': self.get('healthcheck-interval-seconds'),
              'timeoutSeconds': self.get('healthcheck-timeout-seconds'),
              'maxConsecutiveFailures': self.get('healthcheck-max-consecutive-failures'),
              'ignoreHttp1xx': False
            }]
        }

    def framework_marathon_string(self):
        return json.dumps(self.framework_marathon_json())

    def director_marathon_json(self, cluster):
        director_marathon_conf = {
           'id': '/riak-director',
           'cmd': self.get_any('director', 'cmd'),
           'cpus': 0.5,
           'mem': 500.0,
           'ports': [0,0,0,0],
           'instances': 1,
           'env':{
              'USE_SUPER_CHROOT': self.get('super-chroot'),
              'DIRECTOR_ZK': self.get('zk'),
              'DIRECTOR_FRAMEWORK': self.get('framework-name'),
              'DIRECTOR_CLUSTER': cluster
           },
           'uris':[self.get_any('director', 'url')],
           'healthChecks':[
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
            director_marathon_conf['acceptedResourceRoles'] = [ 'public' ]
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
        if subkey2 != None and subkey2 != None:
            conf = self._config
            return self._config[key][subkey1][subkey2]
        else:
            return self._config[key][subkey1]
    def _merge(self, override):
        tmp = self._config.copy()
        tmp.update(override)
        self._config = tmp

##########################################################
######################## Marathon ########################
##########################################################

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

##########################################################
################## Riak Mesos Framework ##################
##########################################################

def format_json_array_keys(description, json_str, failure):
    try:
        obj_arr = json.loads(json_str)
        print(description + '[' + ', '.join(obj_arr.keys()) + ']')
    except:
        print(description + failure)

def format_json_object(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        print(description)
        if key == '':
            print(json.dumps(obj))
        else:
            print(json.dumps(obj[key]))
    except:
        print(description + failure)

def format_json_fact(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        if key == '':
            print(description + json.dumps(obj))
        else:
            print(description + json.dumps(obj[key]))
    except:
        print(description + failure)

def validate_arg(opt, arg, arg_type = 'string'):
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

def extract_option(args, name, default, arg_type = 'string'):
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
    debug(debug_flag, 'HTTP Status: '+ str(r.status_code))
    debug(debug_flag, 'HTTP Response Text: '+ r.text)

def debug(debug_flag, debug_string):
    if debug_flag:
        print('[DEBUG]' + debug_string + '[/DEBUG]')

def run(args):
    args, config_file = extract_option(args, '--config', '/etc/riak-mesos/config.json')
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

    config = Config(None)
    if os.path.isfile(config_file):
        config = Config(config_file)

    if cmd == 'config':
        if help_flag:
            print('Displays configration')
            return 0
        else:
            try:
                if json_flag:
                    print(config.string())
                else:
                    format_json_object('Framework: ', config.string(), 'riak', '[]')
                    format_json_object('Director: ', config.string(), 'director', '[]')
                    format_json_object('Marathon: ', config.string(), 'marathon', '[]')
            except:
                raise CliError('Unable to generate proxy config for framework: ' + config.get('framework-name'))
        return
    elif cmd == 'framework config' or cmd == 'framework':
        if help_flag:
            print('Displays configration for riak marathon app')
            return 0
        else:
            try:
                format_json_object('Marathon Config: ', config.framework_marathon_string(), '', '[]')
            except:
                raise CliError('Unable to generate config for framework: ' + config.get('framework-name'))
        return
    elif cmd == 'framework uninstall':
        if help_flag:
            print('Removes the Riak Mesos Framework application from Marathon')
            return 0
        else:
            print(output = 'Uninstalling framework...')
            try:
                client = create_client(config.get_any('marathon', 'url'))
                client.remove_app('/' + config.get('framework-name'))
                print('Finished removing ' + '/' + config.get('framework-name') + ' from marathon')
            except Exception as e:
                print('\nUnable to uninstall marathon app: ' + e.message)
        return
    elif cmd == 'framework clean-metadata':
        if help_flag:
            print('Deletes all metadata for the selected Riak Mesos Framework instance')
            return 0
        else:
            try:
                print('\nRemoving zookeeper information\n')
                result = config.zk_command('delete', '/riak/frameworks/' + config.get('framework-name'))
                if result:
                    print(result)
                else:
                    print("Unable to remove framework zookeeper data.")
            except Exception as e:
                print('\nUnable to remove zookeeper metadata for framework: ' + print(e.message))
        return
    elif cmd == 'proxy config' or cmd == 'proxy':
        if help_flag:
            print('Generates a marathon json config using --zookeeper (default is leader.mesos:2181) and --cluster (default is default).')
        else:
            try:
                return config.director_marathon_string(cluster)
            except:
                raise CliError('Unable to generate proxy config for framework: ' + config.get('framework-name'))
        return
    elif cmd == 'proxy install':
        if help_flag:
            print('Installs a riak-mesos-director marathon app on the public Mesos node using --zookeeper (default is leader.mesos:2181) and --cluster (default is default).')
        else:
            try:
                director_json = config.director_marathon_json(cluster)
                client = create_client(config.get_any('marathon', 'url'))
                client.add_app(director_json)
                print('Finished adding ' + director_json['id'] + ' to marathon')
            except Exception as e:
                print(e.message)
                raise CliError('Unable to create marathon app')
            except:
                raise CliError('Unable to communicate with marathon.')
        return
    elif cmd == 'proxy uninstall':
        if help_flag:
            print('Uninstalls the riak-mesos-director marathon app.')
        else:
            try:
                client = create_client(config.get_any('marathon', 'url'))
                client.remove_app('/' + config.get('framework-name') + '-director')
                print('Finished removing ' + '/' + config.get('framework-name') + '-director' + ' from marathon')
            except Exception as e:
                print(e.message)
                raise CliError('Unable to uninstall marathon app')
            except:
                raise CliError('Unable to communicate with marathon.')
        return
    elif cmd == 'proxy endpoints':
        if help_flag:
            print('Lists the endpoints exposed by a riak-mesos-director marathon app --public-dns (default is {{public-dns}}).')
        else:
            try:
                client = create_client(config.get_any('marathon', 'url'))
                app = client.get_app(config.get('framework-name') + '-director')
                # ports = app['ports']
                task = app['tasks'][0]
                ports = task['ports']
                hostname = task['host']
                print('Load Balanced Riak Cluster (HTTP)')
                print('    http://' + hostname + ':' + str(ports[0]))
                print('Load Balanced Riak Cluster (Protobuf)')
                print('    http://' + hostname + ':' + str(ports[1]))
                print('Riak Mesos Director API (HTTP)')
                print('    http://' + hostname + ':' + str(ports[2]))
            except Exception as e:
                print(e)
                raise CliError('Unable to get ports for: riak-director')
        return
    elif cmd == 'framework install':
        if help_flag:
            print('Retrieves a list of cluster names')
            return 0
        else:
            try:
                framework_json = config.framework_marathon_json()
                client = create_client(config.get_any('marathon', 'url'))
                client.add_app(framework_json)
                print('Finished adding ' + framework_json['id'] + ' to marathon')
            except Exception as e:
                print(e.message)
                raise CliError('Unable to create marathon app')
            except:
                raise CliError('Unable to communicate with marathon.')
        return

    service_url = config.api_url() + 'api/v1/'
    debug(debug_flag, 'Service URL: ' + service_url)

    if cmd == 'framework endpoints':
        # TODO impl
        if help_flag:
            print('Retrieves useful endpoints for the framework')
            return 0
        # else:
        #     r = requests.get(service_url + 'clusters')
        #     debug_request(debug_flag, r)
        #     if r.status_code == 200:
        #         format_json_array_keys('Clusters: ', r.text, '[]')
        #     else:
        #         print('No clusters created')
    elif cmd == 'cluster config':
        if help_flag:
            print('Gets or sets the riak.conf configuration for a cluster, specify cluster id with --cluster and config file location with --file')
        else:
            if riak_file != '':
                with open(riak_file) as data_file:
                    r = requests.post(service_url + 'clusters/' + cluster + '/config', data=data_file)
                    debug_request(debug_flag, r)
                    if r.status_code != 200:
                        print('Failed to set riak.conf, status_code: ' + str(r.status_code))
                    else:
                        print('riak.conf updated')
            else:
                r = requests.get(service_url + 'clusters/' + cluster)
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    format_json_fact('riak.conf: ', r.text, 'RiakConfig', 'Error getting cluster.')
                else:
                    print('Cluster not created.')
    elif cmd == 'cluster config advanced':
        if help_flag:
            print('Gets or sets the advanced.config configuration for a cluster, specify cluster id with --cluster and config file location with --file')
        else:
            if riak_file != '':
                with open(riak_file) as data_file:
                    r = requests.post(service_url + 'clusters/' + cluster + '/advancedConfig', data=data_file)
                    debug_request(debug_flag, r)
                    if r.status_code != 200:
                        print('Failed to set advanced.config, status_code: ' + str(r.status_code))
                    else:
                        print('advanced.config updated')
            else:
                r = requests.get(service_url + 'clusters/' + cluster)
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    format_json_fact('advanced.config: ', r.text, 'AdvancedConfig', 'Error getting cluster.')
                else:
                    print('Cluster not created.')
    elif cmd == 'cluster list' or cmd == 'cluster':
        if help_flag:
            print('Retrieves a list of cluster names')
            return 0
        else:
            r = requests.get(service_url + 'clusters')
            debug_request(debug_flag, r)
            if r.status_code == 200:
                if json_flag:
                    print(r.text)
                else:
                    format_json_array_keys('Clusters: ', r.text, '[]')
            else:
                print('No clusters created')
    elif cmd == 'cluster create':
        if help_flag:
            print('Creates a new cluster. Specify the name with --cluster (default is default).')
        else:
            r = requests.post(service_url + 'clusters/' + cluster, data='')
            debug_request(debug_flag, r)
            if r.text == '' or r.status_code != 200:
                print('Cluster already exists')
            else:
                format_json_fact('Added cluster: ', r.text, 'Name', 'Error creating cluster.')
    elif cmd == 'cluster restart':
        if help_flag:
            print('Performs a rolling restart on a cluster. Specify the name with --cluster (default is default).')
        else:
            r = requests.post(service_url + 'clusters/' + cluster + '/restart', data='')
            debug_request(debug_flag, r)
            if r.status_code == 404:
                print('Cluster does not exist')
            elif r.status_code != 202:
                print('Failed to restart cluster, status code: ' + str(r.status_code))
            else:
                print('Cluster restart initiated')
    elif cmd == 'cluster destroy':
        if help_flag:
            print('Destroys a cluster. Specify the name with --cluster (default is default).')
        else:
            r = requests.delete(service_url + 'clusters/' + cluster, data='')
            debug_request(debug_flag, r)
            if r.status_code != 202:
                print('Failed to destroy cluster, status_code: ' + str(r.status_code))
            else:
                print('Destroyed cluster: ' + cluster)
    elif cmd == 'node list' or cmd == 'node':
        if help_flag:
            print('Retrieves a list of node ids for a given --cluster (default is default).')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            if json_flag:
                print(r.text)
            else:
                format_json_array_keys('Nodes: ', r.text, '[]')
    elif cmd == 'node info':
        if help_flag:
            print('Retrieves a list of node ids for a given --cluster (default is default).')
        else:
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            node_json = json.loads(r.text)
            print('HTTP: http://' + node_json[node]['Hostname'] + ':' + str(node_json[node]['TaskData']['HTTPPort']))
            print('PB  : ' + node_json[node]['Hostname'] + ':' + str(node_json[node]['TaskData']['PBPort']))
            format_json_object('Node: ', r.text, node, '{}')
    elif cmd == 'node add':
        if help_flag:
            print('Adds one or more (using --nodes) nodes to a --cluster (default is default).')
        else:
            for x in range(0, num_nodes):
                r = requests.post(service_url + 'clusters/' + cluster + '/nodes', data='')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print(r.text)
                else:
                    format_json_fact('New node: ' + config.get('framework-name') + '-' + cluster + '-', r.text, 'SimpleId', 'Error adding node')
                print('')
    elif cmd == 'node remove':
        if help_flag:
            print('Removes a node from the cluster, specify node id with --node')
        else:
            if node == '':
                raise CliError('Node name must be specified')
            else:
                r = requests.delete(service_url + 'clusters/' + cluster + '/nodes/' + node, data='')
                debug_request(debug_flag, r)
                if r.status_code != 202:
                    print('Failed to remove node, status_code: ' + str(r.status_code))
                else:
                    print('Removed node')
    elif cmd == 'node aae-status':
        if help_flag:
            print('Gets the active anti entropy status for a node, specify node id with --node')
        else:
            if node == '':
                raise CliError('Node name must be specified')
            else:
                r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' + node + '/aae')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to get aae-status, status_code: ' + str(r.status_code))
                else:
                    format_json_object('', r.text, 'aae-status', '{}')
    elif cmd == 'node status':
        if help_flag:
            print('Gets the member-status of a node, specify node id with --node')
        else:
            if node == '':
                raise CliError('Node name must be specified')
            else:
                r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' + node + '/status')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to get status, status_code: ' + str(r.status_code))
                else:
                    format_json_object('', r.text, 'status', '{}')
    elif cmd == 'node ringready':
        if help_flag:
            print('Gets the ringready value for a node, specify node id with --node')
        else:
            if node == '':
                raise CliError('Node name must be specified')
            else:
                r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' + node + '/ringready')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to get ringready, status_code: ' + str(r.status_code))
                else:
                    format_json_object('', r.text, 'ringready', '{}')
    elif cmd == 'node transfers':
        if help_flag:
            print('Gets the transfers status for a node, specify node id with --node')
        else:
            if node == '':
                raise CliError('Node name must be specified')
            else:
                r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' + node + '/transfers')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to get transfers, status_code: ' + str(r.status_code))
                else:
                    format_json_object('', r.text, 'transfers', '{}')
    elif cmd == 'node bucket-type create':
        if help_flag:
            print('Creates and activates a bucket type on a node, specify node id with --node')
        else:
            if node == '' or bucket_type == '' or props == '':
                raise CliError('Node name, bucket-type, props must be specified')
            else:
                r = requests.post(service_url + 'clusters/' + cluster + '/nodes/' + node + '/types/' + bucket_type, data=props)
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to create bucket-type, status_code: ' + str(r.status_code))
                    format_json_object('', r.text, '', '{}')
                else:
                    format_json_object('', r.text, '', '{}')
    elif cmd == 'node bucket-type list':
        if help_flag:
            print('Gets the bucket type list from a node, specify node id with --node')
        else:
            if node == '':
                raise CliError('Node name must be specified')
            else:
                r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' + node + '/types')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to get bucket types, status_code: ' + str(r.status_code))
                else:
                    format_json_object('', r.text, 'bucket_types', '{}')
    elif cmd == '':
        print('No commands executed')
    elif cmd.startswith('-'):
        raise CliError('Unrecognized option: ' + cmd)
    else:
        raise CliError('Unrecognized command: ' + cmd)
    print('')
    return 0

def main():
    args = sys.argv[1:] # remove script name
    if is_dcos():
        args = sys.argv[2:] # remove dcos riak
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
        return run(args)
    except CliError as e:
        print('Error: ' + str(e))
        return 1

if __name__ == '__main__':
    main()
