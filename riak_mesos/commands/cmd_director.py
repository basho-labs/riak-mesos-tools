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
def cli():
    pass


@cli.command()
@pass_context
def config(ctx):
    click.echo(ctx.config.director_marathon_string(ctx.config.args['cluster']))


@cli.command('wait-for-service')
@pass_context
def wait_for_service(ctx):
    if util.wait_for_framework(ctx):
        util.wait_for_director(ctx)
        return
    click.echo('Riak Mesos Framework did not respond within ' +
               str(ctx.config.args['timeout']) + 'seconds.')


@cli.command()
@pass_context
def install(ctx):
    director_json = ctx.config.director_marathon_json(
        ctx.config.args['cluster'])
    client = util.marathon_client(ctx.config.get('marathon'))
    client.add_app(director_json)
    click.echo('Finished adding ' + director_json['id'] + ' to marathon.')


@cli.command()
@pass_context
def uninstall(ctx):
    client = util.marathon_client(ctx.config.get('marathon'))
    client.remove_app('/' + ctx.config.args['cluster'] + '-director')
    click.echo('Finished removing ' + '/' + ctx.config.args['cluster'] +
               '-director' + ' from marathon')


@cli.command()
@pass_context
def endpoints(ctx):
    client = util.marathon_client(ctx.config.get('marathon'))
    app = client.get_app('/' + ctx.config.args['cluster'] + '-director')
    task = app['tasks'][0]
    ports = task['ports']
    hostname = task['host']
    endpoints = {
        'framework': ctx.config.get('framework-name'),
        'cluster': ctx.config.args['cluster'],
        'riak_http': hostname + ':' + str(ports[0]),
        'riak_pb': hostname + ':' + str(ports[1]),
        'director_http': hostname + ':' + str(ports[2])
    }
    click.echo(json.dumps(endpoints))
