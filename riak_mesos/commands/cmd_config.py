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


@click.group()
@pass_context
def cli(ctx, **kwargs):
    """Interact with configuration."""
    ctx.init_args(**kwargs)


@cli.command()
@pass_context
def local(ctx, **kwargs):
    """Displays local configuration."""
    ctx.init_args(**kwargs)
    click.echo(ctx.config.string())


@cli.command()
@pass_context
def marathon(ctx, **kwargs):
    """Displays marathon configuration."""
    ctx.init_args(**kwargs)
    click.echo(ctx.config.framework_marathon_string())


@cli.command('riak-versions')
@pass_context
def riak_versions(ctx, **kwargs):
    """Displays available riak-versions."""
    ctx.init_args(**kwargs)
    r = ctx.api_request('get', 'riak/versions')
    click.echo(r.text)
