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
import time

from riak_mesos.cli import pass_context


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
    print("Framework HTTP API: " + ctx.framework_url)


@cli.command()
@pass_context
def install(ctx):
    framework_json = ctx.config.framework_marathon_json()
    client = ctx.marathon_client()
    client.add_app(framework_json)
    click.echo('Finished adding ' + framework_json['id'] + ' to marathon.')


@cli.command()
@pass_context
def status(ctx):
    client = ctx.marathon_client()
    result = client.get_app('/' + ctx.framework)
    click.echo(json.dumps(result))


@cli.command('wait-for-service')
@pass_context
def wait_for_service(ctx):
    def inner_wait_for_framework(seconds):
        if seconds == 0:
            click.echo('Riak Mesos Framework did not respond within ' +
                       str(ctx.timeout) + ' seconds.')
        r = ctx.framework_request('get', 'healthcheck', False)
        if r.status_code == 200:
            click.echo('Riak Mesos Framework is ready.')
            return
        time.sleep(1)
        return inner_wait_for_framework(seconds - 1)

    return inner_wait_for_framework(ctx.timeout)


@cli.command()
@pass_context
def uninstall(ctx):
    click.echo('Uninstalling framework...')
    client = ctx.marathon_client()
    client.remove_app('/' + ctx.framework)
    click.echo('Finished removing ' + '/' + ctx.framework +
               ' from marathon')
    return


@cli.command('clean-metadata')
@click.option('-f', '--force', is_flag=True,
              help='Forcefully remove zookeeper data.')
@pass_context
def clean_metadata(ctx, force):
    fn = ctx.config.get('framework-name')
    if force:
        click.echo('\nRemoving zookeeper information\n')
        result = ctx.zk_command('delete', '/riak/frameworks/' + fn)
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
    r = ctx.master_request('get', '/master/state.json', False)
    ctx.vlog_request(r)
    if r.status_code != 200:
        click.echo('Failed to get state.json from master.')
        return
    js = json.loads(r.text)
    for fw in js['frameworks']:
        if fw['name'] == ctx.framework:
            r = ctx.master_request('post', '/master/teardown',
                                   data='frameworkId='+fw['id'])
            ctx.vlog_request(r)
            click.echo('Finished teardown.')
    return
