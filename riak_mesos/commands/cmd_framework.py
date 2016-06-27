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
from riak_mesos.util import CliError


@click.group()
def cli():
    pass


@cli.command()
@pass_context
def config(ctx):
    obj = ctx.config.framework_marathon_string()
    click.echo(obj)


@cli.command()
@pass_context
def endpoints(ctx):
    service_url = ctx.config.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    print("Framework HTTP API: " + service_url)


@cli.command()
@pass_context
def install(ctx):
    framework_json = ctx.config.framework_marathon_json()
    client = util.marathon_client(ctx.config.get('marathon'))
    client.add_app(framework_json)
    click.echo('Finished adding ' + framework_json['id'] + ' to marathon.')


@cli.command()
@pass_context
def status(ctx):
    client = util.marathon_client(ctx.config.get('marathon'))
    result = client.get_app('/' + ctx.config.get('framework-name'))
    click.echo(json.dumps(result))


@cli.command('wait-for-service')
@pass_context
def wait_for_service(ctx):
    if util.wait_for_framework(ctx):
        click.echo('Riak Mesos Framework is ready.')
        return
    click.echo('Riak Mesos Framework did not respond within ' +
               str(ctx.config.args['timeout']) + ' seconds.')
    return


@cli.command()
@pass_context
def uninstall(ctx):
    click.echo('Uninstalling framework...')
    client = util.marathon_client(ctx.config.get('marathon'))
    client.remove_app('/' + ctx.config.get('framework-name'))
    click.echo('Finished removing ' + '/' + ctx.config.get('framework-name') +
               ' from marathon')
    return


@cli.command('clean-metadata')
@pass_context
def clean_metadata(ctx):
    fn = ctx.config.get('framework-name')
    if ctx.config.args['force_flag']:
        click.echo('\nRemoving zookeeper information\n')
        result = util.zookeeper_command(ctx.config.get('zk'), 'delete',
                                        '/riak/frameworks/' + fn)
        if result:
            click.echo(result)
        else:
            click.echo("Unable to remove framework zookeeper data.")
    else:
        click.echo('\nFramework metadata not removed. Use the --force flag to '
                   'delete all framework zookeeper metadata.\n\n'
                   'WARNING: Running this command with a running instance of '
                   'the Riak Mesos Framework will cause unexpected behavior '
                   'and possible data loss!\n')
    return


@cli.command()
@pass_context
def teardown(ctx):
    r = util.http_request('get', 'http://' + ctx.config.get('master') +
                          '/master/state.json')
    util.debug_request(ctx.config.args['debug_flag'], r)
    if r.status_code != 200:
        click.echo('Failed to get state.json from master.')
        return
    js = json.loads(r.text)
    for fw in js['frameworks']:
        if fw['name'] == ctx.config.get('framework-name'):
            r = util.http_request('post',
                                  'http://' + ctx.config.get('master') +
                                  '/master/teardown',
                                  data='frameworkId='+fw['id'])
            util.debug_request(ctx.config.args['debug_flag'], r)
            click.echo('Finished teardown.')
    return
