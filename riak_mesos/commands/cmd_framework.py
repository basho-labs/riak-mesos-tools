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
    """Interact with an instance of Riak Mesos Framework"""
    ctx.init_args(**kwargs)


@cli.command()
@click.option('--json', is_flag=True,
              help='Enables json output.')
@pass_context
def config(ctx, **kwargs):
    """Displays configration for riak marathon app"""
    ctx.init_args(**kwargs)
    obj = ctx.config.framework_marathon_string()
    click.echo(obj)


@cli.command()
@pass_context
def endpoints(ctx, **kwargs):
    """Retrieves useful endpoints for the framework"""
    ctx.init_args(**kwargs)
    print("Framework HTTP API: " + ctx.get_framework_url())


@cli.command()
@pass_context
def install(ctx, **kwargs):
    """Generates and installs a marathon app for the framework"""
    ctx.init_args(**kwargs)
    framework_json = ctx.config.framework_marathon_json()
    client = ctx.marathon_client()
    client.add_app(framework_json)
    click.echo('Finished adding ' + framework_json['id'] + ' to marathon.')


@cli.command()
@pass_context
def status(ctx, **kwargs):
    """Prints the current marathon app status for the framework."""
    ctx.init_args(**kwargs)
    client = ctx.marathon_client()
    result = client.get_app('/' + ctx.framework)
    click.echo(json.dumps(result))


@cli.command('wait-for-service')
@click.option('--timeout', type=int,
              help='Number of seconds to wait for a response.')
@pass_context
def wait_for_service(ctx, **kwargs):
    """Waits timeout seconds (default is 60) or until Framework is running.
    Specify timeout with --timeout."""
    ctx.init_args(**kwargs)

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
def uninstall(ctx, **kwargs):
    """Removes the Riak Mesos Framework application from Marathon"""
    ctx.init_args(**kwargs)
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
def clean_metadata(ctx, force, **kwargs):
    """Deletes all metadata for the selected Riak Mesos Framework instance"""
    ctx.init_args(**kwargs)
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
def teardown(ctx, **kwargs):
    """Issues a teardown command for each of the matching frameworkIds
    to the Mesos master"""
    ctx.init_args(**kwargs)
    r = ctx.master_request('get', 'master/state.json', False)
    ctx.vlog_request(r)
    if r.status_code != 200:
        click.echo('Failed to get state.json from master.')
        return
    js = json.loads(r.text)
    for fw in js['frameworks']:
        if fw['name'] == ctx.framework:
            r = ctx.master_request('post', 'master/teardown',
                                   data='frameworkId='+fw['id'])
            ctx.vlog_request(r)
            click.echo('Finished teardown.')
    return
