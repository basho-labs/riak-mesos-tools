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
"""DCOS Riak version"""

version = '0.3.1'

usage = '''
Command line utility for the Riak Mesos Framework / DCOS Service.
This utility provides tools for modifying and accessing your Riak
on Mesos installation.

Usage: riak-mesos <subcommands> [options]

Subcommands:
    config
    framework config
    framework install
    framework wait-for-service
    framework clean-metadata
    framework teardown
    framework uninstall
    framework endpoints
    cluster config [--file]
    cluster config advanced [--file]
    cluster list [--json]
    cluster create
    cluster wait-for-service
    cluster endpoints
    cluster restart
    cluster destroy
    node info --node <name>
    node aae-status --node <name>
    node status --node <name>
    node ringready --node <name>
    node transfers --node <name>
    node bucket-type create --node <name> --bucket-type <name>
                            --props "<json>"
    node bucket-type list --node <name>
    node list [--json]
    node remove --node <name>
    node add [--nodes <number>]
    node wait-for-service [--node <name>]
    proxy config
    proxy install
    proxy uninstall
    proxy endpoints
    proxy wait-for-service

Options (available on most commands):
    --config <json-file> (/etc/riak-mesos/config.json)
    --cluster <cluster-name> (default)
    --debug
    --help
    --info
    --version
'''

help_dict = {
    'config': ('Displays configuration'),
    'framework': ('Displays configration for riak marathon app'),
    'framework uninstall':
    ('Removes the Riak Mesos Framework application from Marathon'),
    'framework teardown':
    ('Issues a teardown command for each of the matching frameworkIds to the '
     'Mesos master'),
    'framework clean-metadata':
    ('Deletes all metadata for the selected Riak Mesos Framework instance'),
    'proxy':
    ('Generates a marathon json config using --zookeeper (default is '
     'leader.mesos:2181) and --cluster (default is default).'),
    'proxy install':
    ('Installs a riak-mesos-director marathon app on the public Mesos node '
     'using --zookeeper (default is leader.mesos:2181) and --cluster (default '
     'is default).'),
    'proxy wait-for-service': ('Waits 20 seconds or until proxy is running'),
    'proxy uninstall': ('Uninstalls the riak-mesos-director marathon app.'),
    'proxy endpoints':
    ('Lists the endpoints exposed by a riak-mesos-director marathon app '
     '--public-dns (default is {{public-dns}}).'),
    'framework install':
    ('Generates and installs a marathon app for the framework'),
    'framework wait-for-service':
    ('Waits 60 seconds or until Framework is running'),
    'framework endpoints': ('Retrieves useful endpoints for the framework'),
    'cluster config':
    ('Gets or sets the riak.conf configuration for a cluster, specify cluster '
     'id with --cluster and config file location with --file'),
    'cluster config advanced':
    ('Gets or sets the advanced.config configuration for a cluster, specify '
     'cluster id with --cluster and config file location with --file'),
    'cluster': ('Retrieves a list of cluster names'),
    'cluster create':
    ('Creates a new cluster. Specify the name with --cluster (default is '
     'default).'),
    'cluster wait-for-service':
    ('Iterates over all nodes in cluster and executes node wait-for-service.'),
    'cluster endpoints':
    ('Iterates over all nodes in cluster and prints connection information.'),
    'cluster restart':
    ('Performs a rolling restart on a cluster. Specify the name with '
     '--cluster (default is default).'),
    'cluster destroy':
    ('Destroys a cluster. Specify the name with --cluster (default is '
     'default).'),
    'node':
    ('Retrieves a list of node ids for a given --cluster (default is '
     'default).'),
    'node info':
    ('Retrieves a list of node ids for a given --cluster (default is '
     'default).'),
    'node add':
    ('Adds one or more (using --nodes) nodes to a --cluster (default is '
     'default).'),
    'node wait-for-service': ('Waits 20 seconds or until node is running'),
    'node remove':
    ('Removes a node from the cluster, specify node id with --node'),
    'node aae-status':
    ('Gets the active anti entropy status for a node, specify node id with '
     '--node'),
    'node status':
    ('Gets the member-status of a node, specify node id with --node'),
    'node ringready':
    ('Gets the ringready value for a node, specify node id with --node'),
    'node transfers':
    ('Gets the transfers status for a node, specify node id with --node'),
    'node bucket-type create':
    ('Creates and activates a bucket type on a node, specify node id with '
     '--node'),
    'node bucket-type list':
    ('Gets the bucket type list from a node, specify node id with --node')
}
