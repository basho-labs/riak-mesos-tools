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

import click


def wait_for_node(ctx, node):
    def inner_wait_for_node(seconds):
        if seconds == 0:
            click.echo('Node ' + node + ' did not respond in ' +
                       str(ctx.timeout) + ' seconds.')
            return
        node_data = node_info(ctx, node)
        if node_data['alive'] and node_data['status'] == 'started':
            click.echo('Node ' + node + ' is ready.')
            return
        time.sleep(1)
        return inner_wait_for_node(seconds - 1)

    return inner_wait_for_node(ctx.timeout)


def node_info(ctx, node):
    cluster = ctx.cluster
    fw = ctx.framework
    r = ctx.api_request('get', 'clusters/' + cluster +
                        '/nodes/' + node)
    node_json = json.loads(r.text)
    http_port = str(node_json[node]['location']['http_port'])
    pb_port = str(node_json[node]['location']['pb_port'])
    direct_host = node_json[node]['location']['hostname']
    mesos_dns_cluster = fw + '-' + cluster + '.' + fw + '.mesos'
    r = ctx.node_request('get', node, 'ping', False,
                         headers={'Accept': '*/*'})
    alive = r.status_code == 200
    node_data = {
        'http_direct': direct_host + ':' + http_port,
        'http_mesos_dns': mesos_dns_cluster + ':' + http_port,
        'pb_direct': direct_host + ':' + pb_port,
        'pb_mesos_dns': mesos_dns_cluster + ':' + pb_port,
        'status': node_json[node]['status'],
        'alive': alive
    }
    return node_data


def wait_for_node_status_valid(ctx, node, num_nodes):
    def inner_wait_for_node_status_valid(seconds):
        if seconds == 0:
            click.echo('Cluster ' + ctx.cluster + ' did not respond with ' +
                       str(num_nodes) + ' valid nodes in ' +
                       str(ctx.timeout) + ' seconds.')
            return
        status = node_status(ctx, node)
        if status['status']['valid'] >= num_nodes:
            click.echo('Cluster ' + ctx.cluster + ' is ready.')
            return
        time.sleep(1)
        return inner_wait_for_node_status_valid(seconds - 1)

    return inner_wait_for_node_status_valid(ctx.timeout)


def node_status(ctx, node):
    r = ctx.api_request('get', 'clusters/' + ctx.cluster +
                        '/nodes/' + node + '/status')
    node_json = json.loads(r.text)
    return node_json


def wait_for_node_transfers(ctx, node):
    def inner_wait_for_node_transfers(seconds):
        if seconds == 0:
            click.echo('Node ' + node + ' transfers did not complete in ' +
                       str(ctx.timeout) + 'seconds.')
            return
        r = ctx.api_request('get', 'clusters/' + ctx.cluster +
                            '/nodes/' + node + '/transfers')
        node_json = json.loads(r.text)
        waiting = len(node_json['transfers']['waiting_to_handoff'])
        active = len(node_json['transfers']['active'])
        if seconds % 5 == 0 and seconds != ctx.timeout:
            click.echo(r.text)
        if waiting == 0 and active == 0:
            click.echo('Node ' + node + ' transfers complete.')
            return
        time.sleep(1)
        return inner_wait_for_node_transfers(seconds - 1)

    return inner_wait_for_node_transfers(ctx.timeout)


def get_node_name(ctx, node):
    r = ctx.api_request('get', 'clusters/' + ctx.cluster +
                        '/nodes/' + node)
    node_json = json.loads(r.text)
    return node_json[node]['location']['node_name']
