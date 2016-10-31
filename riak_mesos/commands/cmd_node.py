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
from riak_mesos.util import (get_node_name, wait_for_node,
                             wait_for_node_transfers)


@click.group()
@pass_context
def cli(ctx, **kwargs):
    """Interact with a Riak node"""
    ctx.init_args(**kwargs)


@cli.command('wait-for-service')
@click.argument('node')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def wait_for_service(ctx, **kwargs):
    """Waits timeout seconds (default is 60) or until node is running.
    Specify timeout with --timeout"""
    ctx.init_args(**kwargs)
    wait_for_node(ctx, ctx.node)


@cli.command()
@click.argument('node')
@pass_context
def info(ctx, **kwargs):
    """Retrieves node info"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'clusters/' +
                        ctx.cluster +
                        '/nodes/' + ctx.node)
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
@click.argument('node')
@pass_context
def aae_status(ctx, **kwargs):
    """Gets the active anti entropy status for a node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/aae')
    click.echo(r.text)


@cli.command()
@click.argument('node')
@pass_context
def status(ctx, **kwargs):
    """Gets the member-status of a node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/status')
    click.echo(r.text)


@cli.command()
@click.argument('node')
@pass_context
def ringready(ctx, **kwargs):
    """Gets the ringready value for a node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/ringready')
    click.echo(r.text)


@cli.command()
@click.argument('node')
@click.option('-w-f-s', '--wait-for-service', is_flag=True,
              help='Waits for transfers to complete.')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def transfers(ctx, wait_for_service, **kwargs):
    """Gets the transfers status for a node"""
    ctx.init_args(**kwargs)
    if wait_for_service:
        wait_for_node_transfers(ctx, ctx.node)
        return
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/transfers')
    click.echo(r.text)


@cli.group('bucket-type')
@pass_context
def bucket_type(ctx, **kwargs):
    """Interact with bucket types"""
    ctx.init_args(**kwargs)
    pass


@bucket_type.command('create')
@click.argument('node')
@click.argument('bucket-type')
@click.argument('props')
@pass_context
def bucket_type_create(ctx, bucket_type, props, **kwargs):
    """Creates and activates a bucket type on a node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/types')
    if r.status_code != 200:
        click.echo('Failed to get bucket types, status_code: ' +
                   str(r.status_code))
        return
    if is_bucket_type_exists(bucket_type, r):
        click.echo('Bucket with such type: ' + bucket_type + ' exists')
        return
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node +
                        '/types/' + bucket_type,
                        data=props)
    click.echo(r.text)


@bucket_type.command('update')
@click.argument('node')
@click.argument('bucket-type')
@click.argument('props')
@pass_context
def bucket_type_update(ctx, bucket_type, props, **kwargs):
    """Updates a bucket type on a node"""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node + '/types')
    if r.status_code != 200:
        click.echo('Failed to get bucket types, status_code: ' +
                   str(r.status_code))
        return
    if not is_bucket_type_exists(bucket_type, r):
        click.echo('Bucket with such type: ' + bucket_type + ' does not exist')
        return
    r = ctx.api_request('post',
                        'clusters/' + ctx.cluster +
                        '/nodes/' + ctx.node +
                        '/types/' + bucket_type,
                        data=props)
    click.echo(r.text)


def is_bucket_type_exists(b_type, r):
    bucket_types = json.loads(r.text)['bucket_types']
    for bucket_type in bucket_types:
        if b_type == bucket_type['id']:
            return True
    return False


@bucket_type.command('list')
@click.argument('node')
@pass_context
def bucket_type_list(ctx, **kwargs):
    """Gets the bucket type list from a node"""
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
@click.argument('node')
@click.option('--file', 'log_file',
              help='Log file to view.', default='console.log')
@click.option('--lines', type=int, default=500,
              help='Number of log lines to view.')
@pass_context
def log_tail(ctx, log_file, lines, **kwargs):
    """Shows tail of log file for a node, filename with --file
    and number of lines with --lines"""
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
@click.argument('node')
@pass_context
def log_list(ctx, **kwargs):
    """Lists the available log files for a node"""
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
@click.argument('node')
@pass_context
def stats(ctx, **kwargs):
    """Shows the statistics for a node"""
    ctx.init_args(**kwargs)
    r = ctx.framework_request('get', 'riak/nodes/' +
                              ctx.node + '/stats',
                              headers={'Accept': '*/*'})
    if r.status_code != 200:
        click.echo('Failed to get stats, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)
