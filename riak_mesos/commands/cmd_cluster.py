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
@click.argument('cluster')
@click.option('--nodes', type=int,
              help='Number of nodes to wait for.', default=1)
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def wait_for_service(ctx, nodes, **kwargs):
    """Iterates over all nodes in cluster and executes node wait-for-service.
    Optionally waits until the number of nodes (specified by --nodes) at
    minimum are joined to the cluster."""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' + ctx.cluster + '/nodes')
    if r.status_code != 200:
        click.echo(r.text)
        return
    js = json.loads(r.text)
    ctx.vlog(nodes)
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
    else:
        click.echo("No nodes have been added to cluster " + ctx.cluster)


@cli.command()
@click.argument('cluster')
@pass_context
def endpoints(ctx, **kwargs):
    """Iterates over all nodes in cluster and prints connection information."""
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
@click.argument('cluster')
@pass_context
def info(ctx, **kwargs):
    """Gets current metadata about a cluster."""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' +
                        ctx.cluster)
    click.echo(r.text)


@cli.command('riak-version')
@click.argument('cluster')
@click.argument('riak_vsn')
@pass_context
def riak_version(ctx, riak_vsn, **kwargs):
    """Sets the riak version for a given cluster"""
    ctx.init_args(**kwargs)
    url = 'clusters/' + ctx.cluster + '/riak_version'
    r = ctx.api_request('put', url, data=riak_vsn,
            headers={'Accept': '*/*', 'Content-Type': 'plain/text'})
    click.echo(r.text)


@cli.command()
@click.argument('cluster')
@click.option('-d', '--delete', is_flag=True,
              help='Delete the cluster\'s riak.conf file.')
@click.option('--file', 'riak_file',
              type=click.Path(exists=True, file_okay=True,
                              resolve_path=True),
              help='Cluster riak.conf file to save.')
@pass_context
def config(ctx, delete, riak_file, **kwargs):
    """Gets or sets the riak.conf configuration for a cluster, specify config
    file location with --file."""
    ctx.init_args(**kwargs)
    url = 'clusters/' + ctx.cluster + '/config'
    if delete:
        r = ctx.api_request('delete', url, headers={'Accept': '*/*'}, data='')
        if r.status_code == 404:
            click.echo('No riak.conf set for cluster ' + ctx.cluster)
        else:
            click.echo(r.text)
    elif riak_file is None:
        r = ctx.api_request('get', url, headers={'Accept': '*/*'})
        if r.status_code == 404:
            click.echo('No riak.conf set for cluster ' + ctx.cluster)
        else:
            click.echo(r.text)
    else:
        with open(riak_file) as data_file:
            payload = data_file.read()
            r = ctx.api_request(
                'put', url,
                data=payload,
                headers={'Accept': '*/*',
                         'Content-Type': 'plain/text'})
            click.echo(r.text)


@cli.command('config-advanced')
@click.argument('cluster')
@click.option('-d', '--delete', is_flag=True,
              help='Delete the cluster\'s advanced.config file.')
@click.option('--file', 'advanced_file',
              type=click.Path(exists=True, file_okay=True,
                              resolve_path=True),
              help='Cluster advanced.config file to save.')
@pass_context
def config_advanced(ctx, delete, advanced_file, **kwargs):
    """Gets or sets the advanced.config configuration for a cluster, specify
    config file location with --file."""
    ctx.init_args(**kwargs)
    url = 'clusters/' + ctx.cluster + '/advancedConfig'
    if delete:
        r = ctx.api_request('delete', url, headers={'Accept': '*/*'}, data='')
        if r.status_code == 404:
            click.echo('No advanced.config set for cluster ' + ctx.cluster)
        else:
            click.echo(r.text)
    elif advanced_file is None:
        r = ctx.api_request('get', url,
                            headers={'Accept': '*/*'})
        if r.status_code == 404:
            click.echo('No advanced.config set for cluster ' + ctx.cluster)
        else:
            click.echo(r.text)
    else:
        with open(advanced_file) as data_file:
            payload = data_file.read()
            r = ctx.api_request('put', 'clusters/' +
                                ctx.cluster +
                                '/advancedConfig',
                                data=payload,
                                headers={'Accept': '*/*',
                                         'Content-Type': 'plain/text'})
            click.echo(r.text)


@cli.command('list')
@click.option('-o', '--output-file', type=click.File('wb'),
              help='Output file.')
@pass_context
def cluster_list(ctx, output_file, **kwargs):
    """Retrieves a list of clusters"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters')
    if r.status_code != 200:
        click.echo(r.text)
        return
    if output_file is not None:
        output_file.write(r.text)
    click.echo(r.text)


@cli.command('set')
@click.argument('input_file', type=click.Path(exists=True, file_okay=True,
                                              resolve_path=True))
@pass_context
def set_list(ctx, input_file, **kwargs):
    """Sets list of clusters"""
    with open(input_file) as data_file:
        data = data_file.read()
    ctx.init_args(**kwargs)
    r = ctx.api_request('put', 'clusters',
                        headers={'Content-Type': 'application/json'},
                        data=data)
    click.echo(r.text)


@cli.command()
@click.argument('cluster')
@click.argument('riak_version')
@pass_context
def create(ctx, riak_version, **kwargs):
    """Creates a new cluster."""
    ctx.init_args(**kwargs)
    data = json.dumps({'riak_version': riak_version})
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster + '/create',
                        headers={'Content-Type': 'application/json'},
                        data=data)
    click.echo(r.text)


@cli.command()
@click.argument('cluster')
@pass_context
def restart(ctx, **kwargs):
    """Performs a rolling restart on a cluster."""
    ctx.init_args(**kwargs)
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster +
                        '/restart', data='')
    click.echo(r.text)


@cli.command()
@click.argument('cluster')
@pass_context
def destroy(ctx, **kwargs):
    """Destroys a cluster."""
    ctx.init_args(**kwargs)
    r = ctx.api_request('delete', 'clusters/' +
                        ctx.cluster, data='')
    click.echo(r.text)


@cli.command('add-node')
@click.argument('cluster')
@click.option('--nodes', type=int, default=1,
              help='Number of nodes to add.')
@pass_context
def add_node(ctx, nodes, **kwargs):
    """Adds one or more (using --nodes) nodes."""
    ctx.init_args(**kwargs)
    for x in range(0, nodes):
        r = ctx.api_request('post', 'clusters/' +
                            ctx.cluster + '/nodes', data='')
        click.echo(r.text)
