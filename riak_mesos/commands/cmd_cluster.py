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

import click

from riak_mesos.cli import pass_context
from riak_mesos.util import (node_info, wait_for_node,
                             wait_for_node_status_valid)


@click.group()
@pass_context
def cli(ctx, **kwargs):
    """Interact with Riak clusters"""
    ctx.init_args(**kwargs)


@cli.command('wait-for-service')
@click.option('--nodes', type=int,
              help='Number of nodes to wait for.')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def wait_for_service(ctx, nodes, **kwargs):
    """Iterates over all nodes in cluster and executes node wait-for-service.
    Optionally waits until the number of nodes (specified by --nodes) at
    minimum are joined to the cluster"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' + ctx.cluster + '/nodes')
    js = json.loads(r.text)
    num_nodes = len(js['nodes'])
    total_timeout = ctx.timeout
    if num_nodes > 0:
        ctx.timeout = max(total_timeout / num_nodes, 1)
        for k in js['nodes']:
            wait_for_node(ctx, k)
    if num_nodes >= nodes:
        # Okay, need to divide up the timeout properly
        ctx.timeout = total_timeout
        wait_for_node_status_valid(ctx, js['nodes'][0], nodes)


@cli.command()
@pass_context
def endpoints(ctx, **kwargs):
    """Iterates over all nodes in cluster and prints connection information"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' +
                        ctx.cluster + '/nodes')
    cluster_data = {}
    if r.status_code == 200:
        js = json.loads(r.text)
        for k in js["nodes"]:
            cluster_data[k] = node_info(ctx, k)
        click.echo(json.dumps(cluster_data))
    else:
        click.echo(r.text)


@cli.command()
@pass_context
def info(ctx, **kwargs):
    """Gets current metadata about a cluster"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' +
                        ctx.cluster)
    click.echo(r.text)


@cli.command()
@click.option('--file', 'riak_file',
              type=click.Path(exists=True, file_okay=True,
                              resolve_path=True),
              help='Cluster riak.conf file to save.')
@pass_context
def config(ctx, riak_file, **kwargs):
    """Gets or sets the riak.conf configuration for a cluster, specify cluster
    id with --cluster and config file location with --file"""
    ctx.init_args(**kwargs)
    if riak_file is None:
        r = ctx.api_request('get', 'clusters/' +
                            ctx.cluster + '/config',
                            headers={'Accept': '*/*'})
        click.echo(r.text)
    else:
        with open(riak_file) as data_file:
            r = ctx.api_request('put', 'clusters/' +
                                ctx.cluster + '/config',
                                data=data_file,
                                headers={'Accept': 'plain/text'})
            click.echo(r.text)


@cli.command('config-advanced')
@click.option('--file', 'advanced_file',
              type=click.Path(exists=True, file_okay=True,
                              resolve_path=True),
              help='Cluster advanced.config file to save.')
@pass_context
def config_advanced(ctx, advanced_file, **kwargs):
    """Gets or sets the advanced.config configuration for a cluster, specify
    cluster id with --cluster and config file location with --file"""
    ctx.init_args(**kwargs)
    if advanced_file is None:
        r = ctx.api_request('get', 'clusters/' +
                            ctx.cluster + '/advancedConfig',
                            headers={'Accept': '*/*'})
        click.echo(r.text)
    else:
        with open(advanced_file) as data_file:
            r = ctx.api_request('put', 'clusters/' +
                                ctx.cluster +
                                '/advancedConfig',
                                data=data_file,
                                headers={'Accept': 'plain/text'})
            click.echo(r.text)


@cli.command('list')
@pass_context
def cluster_list(ctx, **kwargs):
    """Retrieves a list of cluster names"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters')
    click.echo(r.text)


@cli.command()
@pass_context
def create(ctx, **kwargs):
    """Creates a new cluster. Specify the name with --cluster (default is
    default)"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('put',
                        'clusters/' + ctx.cluster,
                        data='')
    click.echo(r.text)


@cli.command()
@pass_context
def restart(ctx, **kwargs):
    """Performs a rolling restart on a cluster. Specify the name with
    --cluster (default is default)"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster +
                        '/restart', data='')
    click.echo(r.text)


@cli.command()
@pass_context
def destroy(ctx, **kwargs):
    """Destroys a cluster. Specify the name with --cluster (default is
    default)"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('delete', 'clusters/' +
                        ctx.cluster, data='')
    click.echo(r.text)
