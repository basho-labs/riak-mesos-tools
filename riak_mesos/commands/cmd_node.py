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

import click

from riak_mesos.cli import pass_context
from riak_mesos import util
from riak_mesos.util import CliError


@click.group()
@click.option('--cluster',
              help='Changes the cluster to operate on.')
@click.option('--node',
              help='Changes the node to operate on.')
@pass_context
def cli(ctx, cluster, node):
    if cluster is not None:
        ctx.cluster = cluster
    if node is not None:
        ctx.node = node


@cli.command('wait-for-service')
@pass_context
def wait_for_service(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    util.wait_for_node(ctx.config, ctx.node)


@cli.command()
@pass_context
def list(ctx):
    r = util.api_request(ctx.config, 'get', 'clusters/' +
                         ctx.cluster +
                         '/nodes')
    click.echo(r.text)


@cli.command()
@pass_context
def info(ctx):
    r = util.api_request(ctx.config, 'get', 'clusters/' +
                         ctx.cluster +
                         '/nodes/' + ctx.node)
    click.echo(r.text)


@cli.command()
@pass_context
def add(ctx):
    for x in range(0, ctx.config.args['num_nodes']):
        r = util.api_request(ctx.config, 'post', 'clusters/' +
                             ctx.cluster + '/nodes', data='')
        click.echo(r.text)


@cli.command()
@pass_context
def remove(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    requrl = 'clusters/'
    requrl += ctx.cluster + '/nodes/' + ctx.node
    if ctx.config.args['force_flag']:
        requrl += '?force=true'
    r = util.api_request(ctx.config, 'delete',  requrl, data='')
    click.echo(r.text)


@cli.command('aae-status')
@pass_context
def aae_status(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    r = util.api_request(ctx.config, 'get',
                         'clusters/' + ctx.cluster +
                         '/nodes/' + ctx.node + '/aae')
    click.echo(r.text)


@cli.command()
@pass_context
def status(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    r = util.api_request(ctx.config, 'get',
                         'clusters/' + ctx.cluster +
                         '/nodes/' + ctx.node + '/status')
    click.echo(r.text)


@cli.command()
@pass_context
def ringready(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    r = util.api_request(ctx.config, 'get',
                         'clusters/' + ctx.cluster +
                         '/nodes/' + ctx.node + '/ringready')
    click.echo(r.text)


@cli.command()
@pass_context
def transfers(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    r = util.api_request(ctx.config, 'get',
                         'clusters/' + ctx.cluster +
                         '/nodes/' + ctx.node + '/transfers')
    click.echo(r.text)


@cli.command('transfers wait-for-service')
@pass_context
def transfers_wait_for_service(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    util.wait_for_node_transfers(ctx.config, ctx.node)


@cli.group('bucket-type')
@pass_context
def bucket_type(ctx):
    pass


@bucket_type.command('create')
@pass_context
def bucket_type_create(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    if ctx.config.args['bucket_type'] == '':
        raise CliError('Bucket-Type must be specified')
    if ctx.config.args['props'] == '':
        raise CliError('Props must be specified')
    r = util.api_request(ctx.config, 'post',
                         'clusters/' + ctx.cluster +
                         '/nodes/' + ctx.node +
                         '/types/' + ctx.config.args['bucket_type'],
                         data=ctx.config.args['props'])
    click.echo(r.text)


@bucket_type.command('list')
@pass_context
def bucket_type_list(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    r = util.api_request(ctx.config, 'get',
                         'clusters/' + ctx.cluster +
                         '/nodes/' + ctx.node + '/types')
    click.echo(r.text)


@cli.command('log list')
@pass_context
def log_list(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    node_name = util.get_node_name(ctx.config, ctx.node)
    r = util.api_request(ctx.config, 'get', 'explore/clusters/' +
                         ctx.cluster + '/nodes/' +
                         node_name + '/log/files')
    if r.status_code != 200:
        click.echo('Failed to get log files, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)


@cli.command()
@pass_context
def log(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    if ctx.config.args['riak_file'] == '':
        raise CliError('Log file must be specified')
    node_name = util.get_node_name(ctx.config, ctx.node)
    r = util.api_request(ctx.config, 'get', 'explore/clusters/' +
                         ctx.cluster + '/nodes/' +
                         node_name + '/log/files/' +
                         ctx.config.args['riak_file'] + '?rows=' +
                         ctx.config.args['lines'])
    if r.status_code != 200:
        click.echo('Failed to get log files, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)


@cli.command()
@pass_context
def stats(ctx):
    if ctx.node == '':
        raise CliError('Node name must be specified')
    r = util.api_request(ctx.config, 'get', 'riak/nodes/' +
                         ctx.node + '/stats')
    if r.status_code != 200:
        click.echo('Failed to get stats, status_code: ' +
                   str(r.status_code))
    else:
        click.echo(r.text)
