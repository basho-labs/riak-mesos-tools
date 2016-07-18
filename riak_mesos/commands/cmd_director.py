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

from riak_mesos.cli import pass_context


@click.group()
@pass_context
def cli(ctx, **kwargs):
    """Interact with an instance of Riak Mesos Director smart proxy"""
    ctx.init_args(**kwargs)


@cli.command()
@pass_context
def config(ctx, **kwargs):
    """Generates a marathon json config using --zookeeper (default is
    leader.mesos:2181) and --cluster (default is default)"""
    ctx.init_args(**kwargs)
    ctx.config.from_marathon(ctx)
    click.echo(ctx.config.director_marathon_string(ctx.cluster))


@cli.command('wait-for-service')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def wait_for_service(ctx, **kwargs):
    """Waits --timeout seconds or until director is running"""
    ctx.init_args(**kwargs)

    def inner_wait_for_director(seconds):
        try:
            if seconds == 0:
                click.echo('Director did not respond in ' + str(ctx.timeout) +
                           ' seconds.')

            client = ctx.marathon_client()
            app = client.get_app('/' + ctx.cluster + '-director')
            if len(app['tasks']) == 0:
                click.echo("Director is not installed.")
                return
            if app['tasksHealthy'] != 0:
                click.echo("Director is ready.")
                return
        except:
            pass
        time.sleep(1)
        return inner_wait_for_director(seconds - 1)

    return inner_wait_for_director(ctx.timeout)


@cli.command()
@pass_context
def install(ctx, **kwargs):
    """Installs a riak-mesos-director marathon app on the public Mesos node
    using --cluster (default is default)"""
    ctx.init_args(**kwargs)
    ctx.config.from_marathon(ctx)
    director_json = ctx.config.director_marathon_json(
        ctx.cluster)
    client = ctx.marathon_client()
    client.add_app(director_json)
    click.echo('Finished adding ' + director_json['id'] + ' to marathon.')


@cli.command()
@pass_context
def uninstall(ctx, **kwargs):
    """Uninstalls the riak-mesos-director marathon app"""
    ctx.init_args(**kwargs)
    client = ctx.marathon_client()
    client.remove_app('/' + ctx.cluster + '-director')
    click.echo('Finished removing ' + '/' + ctx.cluster +
               '-director' + ' from marathon')


@cli.command()
@pass_context
def endpoints(ctx, **kwargs):
    """Lists the endpoints exposed by a riak-mesos-director marathon app"""
    ctx.init_args(**kwargs)
    client = ctx.marathon_client()
    app = client.get_app('/' + ctx.cluster + '-director')
    if len(app['tasks']) == 0:
        click.echo("Director is not installed.")
        return
    task = app['tasks'][0]
    ports = task['ports']
    hostname = task['host']
    director_endpoints = {
        'framework': ctx.framework,
        'cluster': ctx.cluster,
        'riak_http': hostname + ':' + str(ports[0]),
        'riak_pb': hostname + ':' + str(ports[1]),
        'director_http': hostname + ':' + str(ports[2])
    }
    click.echo(json.dumps(director_endpoints))
