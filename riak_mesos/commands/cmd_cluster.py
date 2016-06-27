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
import json

from riak_mesos.cli import pass_context
from riak_mesos import util


@click.group()
@click.option('--cluster',
              help='Changes the cluster to operate on.')
@pass_context
def cli(ctx, cluster):
    if cluster is not None:
        ctx.cluster = cluster


@cli.command('wait-for-service')
@pass_context
def wait_for_service(ctx):
    if util.wait_for_framework(ctx):
        r = util.api_request(ctx, 'get', 'clusters/' +
                             ctx.cluster + '/nodes')
        js = json.loads(r.text)
        # Timeout must be at least 1 second
        num_nodes = len(js['nodes'])
        total_timeout = ctx.args['timeout']
        if num_nodes > 0:
            ctx.args['timeout'] = max(total_timeout / num_nodes, 1)
            for k in js['nodes']:
                util.wait_for_node(ctx, k)
        if num_nodes >= ctx.args['num_nodes']:
            # Okay, need to divide up the timeout properly
            ctx.args['timeout'] = total_timeout
            util.wait_for_node_status_valid(ctx, js['nodes'][0])
        return
    click.echo('Riak Mesos Framework did not respond within ' +
               str(ctx.args['timeout']) + 'seconds.')
    return


@cli.command()
@pass_context
def endpoints(ctx):
    if util.wait_for_framework(ctx):
        r = util.api_request(ctx, 'get', 'clusters/' +
                             ctx.cluster + '/nodes')
        cluster_data = {}
        if r.status_code == 200:
            js = json.loads(r.text)
            for k in js["nodes"]:
                cluster_data[k] = util.node_info(ctx, k)
            click.echo(json.dumps(cluster_data))
            return
        else:
            click.echo(r.text)
            return
    click.echo('Riak Mesos Framework did not respond within ' +
               str(ctx.args['timeout']) + 'seconds.')


@cli.command()
@pass_context
def info(ctx):
    r = util.api_request(ctx, 'get', 'clusters/' +
                         ctx.cluster)
    click.echo(r.text)


@cli.command()
@pass_context
def config(ctx):
    if ctx.args['riak_file'] == '':
        r = util.api_request(ctx, 'get', 'clusters/' +
                             ctx.cluster + '/config')
        click.echo(r.text)
    else:
        with open(ctx.args['riak_file']) as data_file:
            r = util.api_request(ctx, 'put', 'clusters/' +
                                 ctx.cluster + '/config',
                                 data=data_file)
            click.echo(r.text)


@cli.command()
@pass_context
def config_advanced(ctx):
    if ctx.args['riak_file'] == '':
        r = util.api_request(ctx, 'get', 'clusters/' +
                             ctx.cluster + '/advancedConfig')
        click.echo(r.text)
    else:
        with open(ctx.args['riak_file']) as data_file:
            r = util.api_request(ctx, 'put', 'clusters/' +
                                 ctx.cluster +
                                 '/advancedConfig',
                                 data=data_file)
            click.echo(r.text)


@cli.command()
@pass_context
def list(ctx):
    r = util.api_request(ctx, 'get', 'clusters')
    click.echo(r.text)


@cli.command()
@pass_context
def create(ctx):
    r = util.api_request(ctx, 'put',
                         'clusters/' + ctx.cluster,
                         data='')
    click.echo(r.text)


@cli.command()
@pass_context
def restart(ctx):
    r = util.api_request(ctx, 'post',
                         'clusters/' + ctx.cluster +
                         '/restart', data='')
    click.echo(r.text)


@cli.command()
@pass_context
def destroy(ctx):
    r = util.api_request(ctx, 'delete', 'clusters/' +
                         ctx.cluster, data='')
    click.echo(r.text)
