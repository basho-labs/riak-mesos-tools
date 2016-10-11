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

from riak_mesos.cli import CliError, pass_context
from riak_mesos.util import (get_node_name, wait_for_node,
                             wait_for_node_transfers)


@click.group()
@pass_context
def cli(ctx, **kwargs):
    """Interact with a Riak node"""
    ctx.init_args(**kwargs)


@cli.command('wait-for-service')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def wait_for_service(ctx, **kwargs):
    """Waits timeout seconds (default is 60) or until node is running.
    Specify timeout with --timeout"""
    ctx.init_args(**kwargs)
    wait_for_node(ctx, ctx.node)


@cli.command('list')
@pass_context
def node_list(ctx, **kwargs):
    """Retrieves a list of node ids for a given --cluster (default is
    default)"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' +
                        ctx.cluster +
                        '/nodes')
    click.echo(r.text)


@cli.command()
@pass_context
def info(ctx, **kwargs):
    """Retrieves node info"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' +
                        ctx.cluster +
                        '/nodes/' + ctx.node)
    click.echo(r.text)


@cli.command()
@click.option('--nodes', type=int, default=1,
              help='Number of nodes to add.')
@pass_context
def add(ctx, nodes, **kwargs):
    """Adds one or more (using --nodes) nodes to a --cluster (default is
    default)"""
    ctx.init_args(**kwargs)
    for x in range(0, nodes):
        r = ctx.api_request('post', 'clusters/' +
                            ctx.cluster + '/nodes', data='')
        click.echo(r.text)


@cli.command()
@click.argument('node')
@click.option('-f', '--force', is_flag=True,
              help='Forcefully remove node.')
@pass_context
def remove(ctx, force, **kwargs):
    """Removes a node from the cluster"""
    ctx.init_args(**kwargs)
    requrl = 'clusters/'
    requrl += ctx.cluster + '/nodes/' + ctx.node
    if force:
        requrl += '?force=true'
    r = ctx.api_request('delete', requrl, data='')
    click.echo(r.text)


@cli.command('aae-status')
@pass_context
def aae_status(ctx, **kwargs):
    """Gets the active anti entropy status for a node, specify node id with
    --node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/aae')
    click.echo(r.text)


@cli.command()
@pass_context
def status(ctx, **kwargs):
    """Gets the member-status of a node, specify node id with --node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/status')
    click.echo(r.text)


@cli.command()
@pass_context
def ringready(ctx, **kwargs):
    """Gets the ringready value for a node, specify node id with --node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/ringready')
    click.echo(r.text)


@cli.group(invoke_without_command=True)
@pass_context
def transfers(ctx, **kwargs):
    """Gets the transfers status for a node, specify node id with --node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/transfers')
    click.echo(r.text)


@cli.command('transfers wait-for-service')
def _transfers_wait_for_service():
    """Waits for transfers to complete, specify node id with --node"""
    pass


@transfers.command('wait-for-service')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def transfers_wait_for_service(ctx, **kwargs):
    """Waits for transfers to complete, specify node id with --node"""
    ctx.init_args(**kwargs)
    wait_for_node_transfers(ctx, ctx.node)


@cli.group('bucket-type')
@pass_context
def bucket_type(ctx, **kwargs):
    """Interact with bucket types"""
    ctx.init_args(**kwargs)
    pass


@bucket_type.command('create')
@click.option('--bucket-type', 'b_type',
              help='Bucket type name.')
@click.option('--props',
              help='Bucket type properties json.')
@pass_context
def bucket_type_create(ctx, b_type, props, **kwargs):
    """Creates and activates a bucket type on a node, specify node id with
    --node, bucket type with --bucket-type, and JSON props with --props"""
    ctx.init_args(**kwargs)
    if b_type is None:
        raise CliError('--bucket-type must be specified')
    if props is None:
        raise CliError('--props JSON must be specified')
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/types')
    if r.status_code != 200:
        click.echo('Failed to get bucket types, status_code: ' +
                   str(r.status_code))
        return
    if is_bucket_type_exists(b_type, r):
        click.echo('Bucket with such type: ' + b_type + ' exists')
        return
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node +
                        '/types/' + b_type,
                        data=props)
    click.echo(r.text)


@bucket_type.command('update')
@click.option('--bucket-type', 'b_type',
              help='Bucket type name.')
@click.option('--props',
              help='Bucket type properties json.')
@pass_context
def bucket_type_update(ctx, b_type, props, **kwargs):
    """Updates a bucket type on a node, specify node id with
    --node, bucket type with --bucket-type, and JSON props with --props"""
    ctx.init_args(**kwargs)
    if b_type is None:
        raise CliError('--bucket-type must be specified')
    if props is None:
        raise CliError('--props JSON must be specified')
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/types')
    if r.status_code != 200:
        click.echo('Failed to get bucket types, status_code: ' +
                   str(r.status_code))
        return
    if not is_bucket_type_exists(b_type, r):
        click.echo('Bucket with such type: ' + b_type + ' does not exist')
        return
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node +
                        '/types/' + b_type,
                        data=props)
    click.echo(r.text)


def is_bucket_type_exists(b_type, r):
    bucket_types = json.loads(r.text)['bucket_types']
    for bucket_type in bucket_types:
        if b_type == bucket_type['id']:
            return True
    return False


@bucket_type.command('list')
@pass_context
def bucket_type_list(ctx, **kwargs):
    """Gets the bucket type list from a node, specify node id with --node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/types')
    click.echo(r.text)


@cli.group()
@pass_context
def log(ctx, **kwargs):
    """Interact with node log files"""
    ctx.init_args(**kwargs)
    pass


@log.command('tail')
@click.option('--file', 'log_file',
              help='Log file to view.', default='console.log')
@click.option('--lines', type=int, default=500,
              help='Number of log lines to view.')
@pass_context
def log_tail(ctx, log_file, lines, **kwargs):
    """Shows tail of log file for a node, specify node id with --node,
    filename with --file, and number of lines with --lines"""
    ctx.init_args(**kwargs)
    node_name = get_node_name(ctx, ctx.node)
    r = ctx.framework_request('get', 'explore/clusters/' +
                              ctx.cluster + '/nodes/' +
                              node_name + '/log/files/' +
                              log_file + '?rows=' + str(lines),
                              headers={'Accept': '*/*'})
    if r.status_code != 200:
        click.echo('Failed to get log files, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)


@log.command('list')
@pass_context
def log_list(ctx, **kwargs):
    """Lists the available log files for a node, specify node id with --node"""
    ctx.init_args(**kwargs)
    node_name = get_node_name(ctx, ctx.node)
    r = ctx.framework_request('get', 'explore/clusters/' +
                              ctx.cluster + '/nodes/' +
                              node_name + '/log/files',
                              headers={'Accept': '*/*'})
    if r.status_code != 200:
        click.echo('Failed to get log files, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)


@cli.command()
@pass_context
def stats(ctx, **kwargs):
    """Shows the statistics for a node, specify node id with --node"""
    ctx.init_args(**kwargs)
    r = ctx.framework_request('get', 'riak/nodes/' +
                              ctx.node + '/stats',
                              headers={'Accept': '*/*'})
    if r.status_code != 200:
        click.echo('Failed to get stats, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)
