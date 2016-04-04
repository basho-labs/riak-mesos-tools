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

import requests
from dcos import marathon
from kazoo.client import KazooClient


class CliError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def wait_for_url(url, debug_flag, seconds):
        if seconds == 0:
            return False
        try:
            r = requests.get(url)
            debug_request(debug_flag, r)
            if r.status_code == 200:
                return True
        except Exception as e:
            debug(debug_flag, str(e))
            pass
        time.sleep(1)
        return wait_for_url(url, debug_flag, seconds - 1)


def wait_for_framework(config, debug_flag, seconds):
    if seconds == 0:
        return False
    try:
        healthcheck_url = config.api_url() + 'clusters'
        debug(debug_flag, "Trying " + healthcheck_url)
        if wait_for_url(healthcheck_url, debug_flag, 1):
            return True
    except:
        pass
    time.sleep(1)
    return wait_for_framework(config, debug_flag, seconds - 1)


def wait_for_node(config, cluster, debug_flag, node, seconds):
    if seconds == 0:
        print('Node ' + node + ' did not respond in 20 seconds.')
        return
    node_data = node_info(config, cluster, debug_flag, node)
    if node_data['alive'] and node_data['status'] == 'started':
        print('Node ' + node + ' is ready.')
        return
    time.sleep(1)
    return wait_for_node(config, cluster, debug_flag, node,
                         seconds - 1)


def node_info(config, cluster, debug_flag, node):
    service_url = config.api_url()
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' + node)
    debug_request(debug_flag, r)
    node_json = json.loads(r.text)
    http_port = str(node_json[node]['location']['http_port'])
    pb_port = str(node_json[node]['location']['http_port'])
    direct_host = node_json[node]['location']['hostname']
    fw = config.get('framework-name')
    mesos_dns_cluster = fw + '-' + cluster + '.' + fw + '.mesos'
    alive = False
    if direct_host != '' and http_port != 'undefined':
        try:
            r = requests.get('http://' + direct_host + ':' + http_port)
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
