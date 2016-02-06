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
import traceback
import requests
import commands

from config import Config, create_client


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
    print('    cluster endpoints')
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
    ('Issues a teardown command for each of the matching frameworkIds to the '
     'Mesos master'),
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
    'framework wait-for-service':
    ('Waits 60 seconds or until Framework is running'),
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
    'cluster endpoints':
    ('Iterates over all nodes in cluster and prints connection information.'),
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
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:
            self.fall = True
            return True
        else:
            return False


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


def test_flag(args, name):
    return name in args


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
    debug(debug_flag, 'HTTP URL: ' + r.url)
    debug(debug_flag, 'HTTP Method: ' + r.request.method)
    debug(debug_flag, 'HTTP Body: ' + str(r.request.body))
    debug(debug_flag, 'HTTP Status: ' + str(r.status_code))
    debug(debug_flag, 'HTTP Response Text: ' + r.text)


def debug(debug_flag, debug_string):
    if debug_flag:
        print('[DEBUG]' + debug_string + '[/DEBUG]')


def wait_for_url(url, debug_flag, seconds):
    if seconds == 0:
        return False
    try:
        r = requests.get(url)
        debug_request(debug_flag, r)
        if r.status_code == 200:
            return True
    except:
        pass
    time.sleep(1)
    return wait_for_url(url, debug_flag, seconds - 1)


def wait_for_framework(config, debug_flag, seconds):
    if seconds == 0:
        return False
    try:
        healthcheck_url = config.api_url() + 'clusters'
        if wait_for_url(healthcheck_url, debug_flag, 1):
            return True
    except:
        pass
    time.sleep(1)
    return wait_for_framework(config, debug_flag, seconds - 1)


def wait_for_node(config, cluster, debug_flag, node, seconds):
    if wait_for_framework(config, debug_flag, 60):
        service_url = config.api_url()
        r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
        debug_request(debug_flag, r)
        node_json = json.loads(r.text)
        if wait_for_url('http://' + node_json[node]['Hostname'] + ':' +
                        str(node_json[node]['TaskData']['HTTPPort']),
                        debug_flag, 20):
            if node_json[node]['CurrentState'] == 3:
                print('Node ' + node + ' is ready.')
                return
            return wait_for_node(config, cluster, debug_flag, node,
                                 seconds - 1)
        print('Node ' + node + ' did not respond in 20 seconds.')
        return
    print('Riak Mesos Framework did not respond within 60 seconds.')
    return


def node_info(config, cluster, debug_flag, node):
    service_url = config.api_url()
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
    debug_request(debug_flag, r)
    fw = config.get('framework-name')
    node_json = json.loads(r.text)
    http_port = str(node_json[node]['TaskData']['HTTPPort'])
    pb_port = str(node_json[node]['TaskData']['PBPort'])
    direct_host = node_json[node]['Hostname']
    mesos_dns_cluster = fw + '-' + cluster + '.' + fw + '.mesos'
    alive = False
    r = requests.get('http://' + direct_host + ':' + http_port)
    debug_request(debug_flag, r)
    if r.status_code == 200:
        alive = True
    node_data = {
        'http_direct': direct_host + ':' + http_port,
        'http_mesos_dns': mesos_dns_cluster + ':' + http_port,
        'pb_direct': direct_host + ':' + pb_port,
        'pb_mesos_dns': mesos_dns_cluster + ':' + pb_port,
        'alive': alive
    }
    return node_data


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

    try:
        commandFunc = getattr(commands, cmd.replace(' ', '_'))
        output = commandFunc()
        print output
    except AttributeError:
        raise CliError('Unrecognized command: ' + cmd)

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

    for case in switch(cmd):
        if case('config'):
            if json_flag:
                print(config.string())
            else:
                ppobj('Framework: ', config.string(), 'riak', '[]')
                ppobj('Director: ', config.string(), 'director', '[]')
                ppobj('Marathon: ', config.string(), 'marathon', '[]')
            break
        if case('framework config', 'framework'):
            obj = config.framework_marathon_string()
            if json_flag:
                print(obj)
            else:
                ppobj('Marathon Config: ', obj, '', '{}')
            break
        if case('framework uninstall'):
            print('Uninstalling framework...')
            fn = config.get('framework-name')
            client = create_client(config.get_any('marathon', 'url'))
            client.remove_app('/' + fn)
            print('Finished removing ' + '/' + fn + ' from marathon')
            break
        if case('framework clean-metadata'):
            fn = config.get('framework-name')
            print('\nRemoving zookeeper information\n')
            result = config.zk_command('delete', '/riak/frameworks/' + fn)
            if result:
                print(result)
            else:
                print("Unable to remove framework zookeeper data.")
            break
        if case('framework teardown'):
            r = requests.get('http://leader.mesos:5050/master/state.json')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get state.json from master.')
                break
            js = json.loads(r.text)
            for fw in js['frameworks']:
                if fw['name'] == config.get('framework-name'):
                    r = requests.post(
                        'http://leader.mesos:5050/master/teardown',
                        data='frameworkId='+fw['id'])
                    debug_request(debug_flag, r)
                    print('Finished teardown.')
            break
        if case('proxy config', 'proxy'):
            print(config.director_marathon_string(cluster))
            break
        if case('proxy install'):
            director_json = config.director_marathon_json(cluster)
            client = create_client(config.get_any('marathon', 'url'))
            client.add_app(director_json)
            print('Finished adding ' + director_json['id'] + ' to marathon.')
            break
        if case('proxy uninstall'):
            client = create_client(config.get_any('marathon', 'url'))
            fn = config.get('framework-name')
            client.remove_app('/' + fn + '-director')
            print('Finished removing ' + '/' + fn + '-director' +
                  ' from marathon')
            break
        if case('proxy endpoints'):
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
            break
        if case('framework install'):
            framework_json = config.framework_marathon_json()
            client = create_client(config.get_any('marathon', 'url'))
            client.add_app(framework_json)
            print('Finished adding ' + framework_json['id'] + ' to marathon.')
            break
        if case('framework wait-for-service'):
            if wait_for_framework(config, debug_flag, 60):
                print('Riak Mesos Framework is ready.')
                break
            print('Riak Mesos Framework did not respond within 60 seconds.')
            break
        if case('node wait-for-service'):
            if node == '':
                raise CliError('Node name must be specified')
            wait_for_node(config, cluster, debug_flag, node, 20)
            break
        if case('cluster wait-for-service'):
            if wait_for_framework(config, debug_flag, 60):
                service_url = config.api_url()
                r = requests.get(service_url + 'clusters/' + cluster +
                                 '/nodes')
                debug_request(debug_flag, r)
                js = json.loads(r.text)
                for k in js.keys():
                    wait_for_node(config, cluster, debug_flag, k, 20)
                break
            print('Riak Mesos Framework did not respond within 60 '
                  'seconds.')
            break
        if case('cluster endpoints'):
            if wait_for_framework(config, debug_flag, 60):
                service_url = config.api_url()
                r = requests.get(service_url + 'clusters/' + cluster +
                                 '/nodes')
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    js = json.loads(r.text)
                    cluster_data = {}
                    for k in js.keys():
                        cluster_data[k] = node_info(config, cluster,
                                                    debug_flag, k)
                    print(json.dumps(cluster_data))
                else:
                    print(r.text)
                break
            print('Riak Mesos Framework did not respond within 60 '
                  'seconds.')
            break
        if case('proxy wait-for-service'):
            if wait_for_framework(config, debug_flag, 60):
                client = create_client(config.get_any('marathon', 'url'))
                app = client.get_app(config.get('framework-name') +
                                     '-director')
                if len(app['tasks']) == 0:
                    print("Proxy is not installed.")
                    break
                task = app['tasks'][0]
                ports = task['ports']
                hostname = task['host']
                if wait_for_url('http://' + hostname + ':' +
                                str(ports[0]), debug_flag, 20):
                    print("Proxy is ready.")
                    break
                print("Proxy did not respond in 20 seconds.")
                break
            print('Riak Mesos Framework did not respond within 60 seconds.')
            break
        if case('framework endpoints'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            print("Framework HTTP API: " + service_url)
            break
        if case('cluster config'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if riak_file == '':
                r = requests.get(service_url + 'clusters/' + cluster)
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    ppfact('riak.conf: ', r.text, 'RiakConfig',
                           'Error getting cluster.')
                else:
                    print('Cluster not created.')
                break
            with open(riak_file) as data_file:
                r = requests.post(service_url + 'clusters/' + cluster +
                                  '/config', data=data_file)
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to set riak.conf, status_code: ' +
                          str(r.status_code))
                else:
                    print('riak.conf updated')
            break
        if case('cluster config advanced'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if riak_file == '':
                r = requests.get(service_url + 'clusters/' + cluster)
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    ppfact('advanced.config: ', r.text, 'AdvancedConfig',
                           'Error getting cluster.')
                else:
                    print('Cluster not created.')
                break
            with open(riak_file) as data_file:
                r = requests.post(service_url + 'clusters/' + cluster +
                                  '/advancedConfig', data=data_file)
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to set advanced.config, status_code: ' +
                          str(r.status_code))
                else:
                    print('advanced.config updated')
            break
        if case('cluster list', 'cluster'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.get(service_url + 'clusters')
            debug_request(debug_flag, r)
            if r.status_code == 200:
                if json_flag:
                    print(r.text)
                else:
                    pparr('Clusters: ', r.text, '[]')
            else:
                print('No clusters created')
            break
        if case('cluster create'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.post(service_url + 'clusters/' + cluster, data='')
            debug_request(debug_flag, r)
            if r.text == '' or r.status_code != 200:
                print('Cluster already exists.')
            else:
                ppfact('Added cluster: ', r.text, 'Name',
                       'Error creating cluster.')
            break
        if case('cluster restart'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
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
            break
        if case('cluster destroy'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.delete(service_url + 'clusters/' + cluster, data='')
            debug_request(debug_flag, r)
            if r.status_code != 202:
                print('Failed to destroy cluster, status_code: ' +
                      str(r.status_code))
            else:
                print('Destroyed cluster: ' + cluster)
            break
        if case('node list', 'node'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            if json_flag:
                print(r.text)
            else:
                pparr('Nodes: ', r.text, '[]')
            break
        if case('node info'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            node_json = json.loads(r.text)
            print('HTTP: http://' + node_json[node]['Hostname'] + ':' +
                  str(node_json[node]['TaskData']['HTTPPort']))
            print('PB  : ' + node_json[node]['Hostname'] + ':' +
                  str(node_json[node]['TaskData']['PBPort']))
            ppobj('Node: ', r.text, node, '{}')
            break
        if case('node add'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            for x in range(0, num_nodes):
                r = requests.post(service_url + 'clusters/' + cluster +
                                  '/nodes', data='')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print(r.text)
                else:
                    ppfact('New node: ' + config.get('framework-name') + '-' +
                           cluster + '-', r.text, 'SimpleId', 'Error adding '
                           'node')
            break
        if case('node remove'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.delete(service_url + 'clusters/' + cluster +
                                '/nodes/' + node, data='')
            debug_request(debug_flag, r)
            if r.status_code != 202:
                print('Failed to remove node, status_code: ' +
                      str(r.status_code))
            else:
                print('Removed node')
            break
        if case('node aae-status'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/aae')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get aae-status, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'aae-status', '{}')
            break
        if case('node status'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/status')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get status, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'status', '{}')
            break
        if case('node ringready'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/ringready')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get ringready, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'ringready', '{}')
            break
        if case('node transfers'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/transfers')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get transfers, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'transfers', '{}')
            break
        if case('node bucket-type create'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '' or bucket_type == '' or props == '':
                raise CliError('Node name, bucket-type, props must be '
                               'specified')
            r = requests.post(service_url + 'clusters/' + cluster + '/nodes/' +
                              node + '/types/' + bucket_type, data=props)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to create bucket-type, status_code: ' +
                      str(r.status_code))
                ppobj('', r.text, '', '{}')
            else:
                ppobj('', r.text, '', '{}')
            break
        if case('node bucket-type list'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/types')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get bucket types, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'bucket_types', '{}')
            break
        if case():
            raise CliError('Unrecognized command: ' + cmd)
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
        print('Riak Mesos Framework Version 0.3.1')
        return 0
    if '--config-schema' in args:
        print('{}')
        return 0

    debug_flag = test_flag(args, '--debug')

    try:
        return_code = run(args)
        print('')
        return return_code
    except requests.exceptions.ConnectionError as e:
        print('ConnectionError: ' + str(e))
        if debug_flag:
            traceback.print_exc()
            raise e
        return 1
    except CliError as e:
        print('CliError: ' + str(e))
        if debug_flag:
            traceback.print_exc()
            raise e
        return 1
    except Exception as e:
        print(e)
        if debug_flag:
            traceback.print_exc()
            raise e
        return 1

if __name__ == '__main__':
    main()
