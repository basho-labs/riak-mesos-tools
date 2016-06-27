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

import json
import time

from dcos import marathon, http
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSException,
                         DCOSHTTPException)
from kazoo.client import KazooClient


class CliError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


def api_request(ctx, method, path, **kwargs):
    service_url = ctx.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")

    verify = True
    if ctx.insecure_ssl:
        verify = False
    r = http_request(method,
                     service_url + path,
                     verify=verify,
                     **kwargs)
    ctx.vlog_request(r)
    return r


def wait_for_director(ctx):
    timeout = ctx.args['timeout']

    def inner_wait_for_director(seconds):
        try:
            if seconds == 0:
                print('Director did not respond in ' + ctx.args['timeout'] +
                      ' seconds.')

            client = marathon_client(ctx.get('marathon'))
            app = client.get_app(ctx.args['cluster'] +
                                 '-director')
            if len(app['tasks']) == 0:
                print("Director is not installed.")
                return
            task = app['tasks'][0]
            ports = task['ports']
            hostname = task['host']
            url = 'http://' + hostname + ':' + str(ports[0])
            r = http_request('get', url)
            if r.status_code == 200:
                print("Director is ready.")
                return
        except:
            pass
        time.sleep(1)
        return inner_wait_for_director(seconds - 1)

    return inner_wait_for_director(timeout)


def wait_for_framework(ctx):
    timeout = ctx.args['timeout']

    def inner_wait_for_framework(seconds):
        try:
            if seconds == 0:
                return False
            r = api_request(ctx, 'get', 'clusters')
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
        return inner_wait_for_framework(seconds - 1)

    return inner_wait_for_framework(timeout)


def wait_for_node(ctx, node):
    timeout = ctx.args['timeout']

    def inner_wait_for_node(seconds):
        if seconds == 0:
            print('Node ' + node + ' did not respond in ' +
                  str(timeout) + 'seconds.')
            return
        node_data = node_info(ctx, node)
        if node_data['alive'] and node_data['status'] == 'started':
            print('Node ' + node + ' is ready.')
            return
        time.sleep(1)
        return inner_wait_for_node(seconds - 1)

    return inner_wait_for_node(timeout)


def wait_for_node_transfers(ctx, node):
    timeout = ctx.args['timeout']
    cluster = ctx.args['cluster']

    def inner_wait_for_node_transfers(seconds):
        if seconds == 0:
            print('Node ' + node + ' transfers did not complete in ' +
                  str(timeout) + 'seconds.')
            return
        r = api_request(ctx, 'get', 'clusters/' + cluster +
                        '/nodes/' + node + '/transfers')
        node_json = json.loads(r.text)
        waiting = len(node_json['transfers']['waiting_to_handoff'])
        active = len(node_json['transfers']['active'])
        if waiting == 0 and active == 0:
            print('Node ' + node + ' transfers complete.')
            return
        time.sleep(1)
        return inner_wait_for_node_transfers(seconds - 1)

    return inner_wait_for_node_transfers(timeout)


def wait_for_node_status_valid(ctx, node):
    timeout = ctx.args['timeout']
    num_valid_nodes = ctx.args['num_nodes']
    cluster = ctx.args['cluster']

    def inner_wait_for_node_status_valid(seconds):
        if seconds == 0:
            print('Cluster ' + cluster + ' did not respond with ' +
                  str(num_valid_nodes) + ' valid nodes in ' +
                  str(timeout) + ' seconds.')
            return
        status = node_status(ctx, node)
        if status['status']['valid'] >= num_valid_nodes:
            print('Cluster ' + cluster + ' is ready.')
            return
        time.sleep(1)
        return inner_wait_for_node_status_valid(seconds - 1)

    return inner_wait_for_node_status_valid(timeout)


def node_status(ctx, node):
    cluster = ctx.args['cluster']
    r = api_request(ctx, 'get', 'clusters/' + cluster +
                    '/nodes/' + node + '/status')
    node_json = json.loads(r.text)
    return node_json


def node_info(ctx, node):
    cluster = ctx.args['cluster']
    fw = ctx.get('framework-name')
    debug_flag = ctx.args['debug_flag']
    r = api_request(ctx, 'get', 'clusters/' + cluster +
                    '/nodes/' + node)
    node_json = json.loads(r.text)
    http_port = str(node_json[node]['location']['http_port'])
    pb_port = str(node_json[node]['location']['pb_port'])
    direct_host = node_json[node]['location']['hostname']
    mesos_dns_cluster = fw + '-' + cluster + '.' + fw + '.mesos'
    alive = False
    if direct_host != '' and http_port != 'undefined':
        try:
            r = http_request('get', 'http://' + direct_host + ':' + http_port)
            debug_request(debug_flag, r)
            alive = r.status_code == 200
        except:
            alive = False
    node_data = {
        'http_direct': direct_host + ':' + http_port,
        'http_mesos_dns': mesos_dns_cluster + ':' + http_port,
        'pb_direct': direct_host + ':' + pb_port,
        'pb_mesos_dns': mesos_dns_cluster + ':' + pb_port,
        'status': node_json[node]['status'],
        'alive': alive
    }
    return node_data


def get_node_name(ctx, node):
    cluster = ctx.args['cluster']
    r = api_request(ctx, 'get', 'clusters/' + cluster +
                    '/nodes/' + node)
    node_json = json.loads(r.text)
    return node_json[node]['location']['node_name']


def marathon_client(marathon_url=None):
    if marathon_url is not None:
        return marathon.Client('http://' + marathon_url)
    else:
        return marathon.create_client()


def zookeeper_command(hosts, command, path):
    try:
        zk = KazooClient(hosts=hosts)
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
    except:
        return False


def debug(debug_flag, debug_string):
    if debug_flag:
        print('[DEBUG]' + debug_string + '[/DEBUG]')


def debug_request(debug_flag, r):
    debug(debug_flag, 'HTTP URL: ' + r.url)
    debug(debug_flag, 'HTTP Method: ' + r.request.method)
    debug(debug_flag, 'HTTP Body: ' + str(r.request.body))
    debug(debug_flag, 'HTTP Status: ' + str(r.status_code))
    debug(debug_flag, 'HTTP Response Text: ' + r.text)


def pparr(description, json_str, failure):
    try:
        obj_arr = json.loads(json_str)
        print(description + '[' + ', '.join(obj_arr.keys()) + ']')
    except:
        print(description + failure)


def ppobj(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        if key == '':
            print(description + json.dumps(obj))
        else:
            print(description + json.dumps(obj[key]))
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


def http_request(method,
                 url,
                 **kwargs):
    try:
        return http.request(method, url, **kwargs)
    except DCOSAuthenticationException as e:
        raise CliError('HTTP Authentication Exception: ' + e.message)
    except DCOSAuthorizationException as e:
        raise CliError('HTTP Authorization Exception: ' + e.message)
    except DCOSHTTPException as e:
        raise CliError('HTTP Exception: ' + str(e))
    except DCOSException as e:
        raise CliError(e.message)
    except Exception as e:
        raise CliError(e.message)
