Riak Mesos Tools
================

CLI and other tools for interacting with the Riak Mesos Framework.

[![image](https://secure.travis-ci.org/basho-labs/riak-mesos-tools.svg)](http://travis-ci.org/basho-labs/riak-mesos-tools)

Requirements
------------

Before getting started with the RMF, there are a few environment and system related requirements that are assumed for the remainder of this tutorial:

-   A Mesos cluster version 0.25.0.
-   Python version 2.7 or above.
-   Operating system is one of: Ubuntu 14.04+, CentOS 7.0+.

Note to DCOS Users
==================

All of the below instructions will work for the `dcos riak` command, just replace `riak-mesos` with `dcos riak`. Some other differences will be pointed out in the corresponding sections.

Installation
============

DCOS Install
------------

-   Create a file at `/etc/riak-mesos/config.json` and use this `config.json <config/config.example.json>` as a template. More information on configuration values can be found below.
-   Append the DCOS Riak package repo to your DCOS repo sources:

        dcos config prepend package.sources https://github.com/basho-labs/riak-mesos-dcos-repo/archive/0.3.1.zip

-   Update packages:

        dcos package update

-   Install the dcos riak subcommand:

        dcos package install riak --options /etc/riak-mesos/config.json

Pip Install
-----------

**Note:** You may need to run `pip uninstall riak-mesos` first to ensure the latest version.

### Install the latest version (master)

``` sourceCode
sudo pip install --upgrade git+https://github.com/basho-labs/riak-mesos-tools.git#egg=riak_mesos
```

### Install the latest tag ###

``` sourceCode
sudo sudo pip install --upgrade git+https://github.com/basho-labs/riak-mesos-tools.git@0.3.1#egg=riak_mesos
```

Quick Install
-------------

The included install.sh script will download and extract this package into `$HOME/bin/riak-mesos-tools`. Using this method does not require DCOS or pip or any of the other dependencies, and should work with most basic Python 2.7+ installations.

``` sourceCode
curl -s -L https://raw.githubusercontent.com/basho-labs/riak-mesos-tools/master/install.sh | sh
```

Create a Configuration File
---------------------------

If your environment differs from the required the default parameters, you may need to create a custom configuration file. Export the default config using this command:

``` sourceCode
riak-mesos config --json | python -m json.tool > config.json
mv config.json /etc/riak-mesos/config.json
```

The resulting `/etc/riak-mesos/config.json` can then be modified to fit your environment. Here is a brief description of some of those values:

-   `riak.url`: Location of the RMF tar ball which contains the actual RMF executables. Following are the current releases.
    -   Ubuntu 14.04 with Golang Executor:

            http://riak-tools.s3.amazonaws.com/riak-mesos/golang/ubuntu/riak_mesos_linux_amd64_0.3.1.tar.gz

    -   Ubuntu 14.04 with Erlang Executor (Mesos 0.26 Only):

            http://riak-tools.s3.amazonaws.com/riak-mesos/erlang/mesos-0.26/ubuntu/riak_mesos_linux_amd64_0.3.1.tar.gz

    -   CentOS/RHEL 7 with Golang Executor:

            http://riak-tools.s3.amazonaws.com/riak-mesos/golang/centos/riak_mesos_linux_amd64_0.3.1.tar.gz

    -   CentOS/RHEL 7 with Erlang Executor (Mesos 0.26 Only):

            http://riak-tools.s3.amazonaws.com/riak-mesos/erlang/mesos-0.26/centos/riak_mesos_linux_amd64_0.3.1.tar.gz
        
-   `riak.master`: The address for the Mesos master. Example values:
    -   `localhost:5050`
    -   `leader.mesos:5050`
    -   `zk://leader.mesos:2181/mesos`
-   `riak.zk`: The address for Zookeeper. Default value is: `leader.mesos:2181`.
-   `riak.cpus`: Amount of CPU resources for the Framework task. Default value is: `0.5`.
-   `riak.mem`: Amount of Memory for the Framework task. Default value is: `2048`.
-   `riak.node.cpus`: Amount of CPU resources per Riak node. Default value is: `1.0`.
-   `riak.node.disk`: Amount of Memory resources per Riak node. Default value is: `8000`.
-   `riak.node.mem`: Amount of Disk resources per Riak node. Default value is: `20000`.
    -   `Note:` To ensure that each Riak node resides on a unique Mesos agent / physical host, this value should be at least 51% of a single Mesos agent's total capacity.
-   `riak.role`: Mesos role for the RMF and tasks. Required for Dynamic Reservations / Persistent Volumes.
    -   **Note:** The Mesos master may need to be restarted with `MESOS_ROLES=riak` or `--roles=riak`.
-   `riak.user`: The user which will run the Riak process and executor. When using the Golang Executor builds, the user may be `root`. If using the Erlang executor, the user must exist on all of the Mesos agents, and **must not be root**.
-   `riak.auth-principal`: The Mesos authentication principal. Required for Dynamic Reservations / Persistent Volumes.
-   `riak.flags`: Any additional flags to pass to the RMF. Default value is: `"-use_reservations"`. Remove this parameter when running Mesos version 0.23 or lower.
-   `director.url`: Location for the RMF smart proxy. The smart proxy will automatically detect changes in the Riak cluster topology based on updates to Zookeeper values stored by each of the running Riak nodes.
-   `director.use-public`: When this is true, the smart proxy will only be deployed on an agent with a public role.
-   `director.cmd`: Legacy versions of the framework may need to modify this.
-   `marathon.url`: Address for Marathon. Default value is: `"http://marathon.mesos:8080"`.

Usage
=====

Try executing `riak-mesos`, `riak-mesos -h`, or `riak-mesos --help` to output the usage instructions.

We'll be covering the majority of the commands in this guide. Here is a brief description of some of them:

-   `riak-mesos config`: Output the current configuration values.
-   `riak-mesos framework`: Interact with the RMF application.
    -   `config`: Output the generated Marathon json application definition for the RMF.
    -   `install`: Install the RMF as a Marathon app.
    -   `uninstall`: Delete the RMF from Marathon.
    -   `wait-for-service`: Waits until the framework's HTTP API returns OK.
    -   `clean-metadata`: Removes Zookeeper metadata stored by the RMF instance.
    -   `teardown`: Issues a teardown call to the Mesos master, killing all tasks related to the RMF instance.
-   `riak-mesos cluster`
    -   `create`: Creates a named Riak cluster (default is `default`) in the RMF using default values for `riak.conf` and `advanced.config`.
    -   `list`: Lists the names of each cluster.
    -   `config [advanced]`: Outputs the configuration values for `riak.conf` and `advanced.config`.
    -   `restart`: Performs a rolling restart of the cluster. If you've upgraded to a new version of the RMF or Riak, restarting the cluster will push the new Riak version while preserving the data directories if you are using persistent volumes.
    -   `destroy`: Kills all Riak node tasks for a cluster, deletes any created persistent volumes, and un-reserves any dynamically reserved resources for the nodes.
    -   `wait-for-service`: Iterates over all of the nodes in the cluster, calling wait-for-service on each.
    -   `endpoints`: Lists each node and connection information for each including HTTP and Protobuf ports and hosts.
-   `riak-mesos node`: Interact with an individual node in the cluster.
    -   `info`: Outputs information about a Riak node stored by the RMF.
    -   `aae-status`: Outputs the active anti entropy status for a node.
    -   `status`: Outputs the member status information for a node.
    -   `ringready`: Outputs the ringready status for a node.
    -   `transfers`: Outputs the active and waiting partition transfers for a node.
    -   `bucket-type`: Interact with bucket types on a node / cluster.
        -   `create`: Creates and activates a bucket type given some properties as json.
        -   `list`: List all bucket types and their properties from a node / cluster.
    -   `list`: List all nodes in a cluster.
    -   `remove`: Kills the task for a node, destroys any created persistent volumes, and un-reserves any dynamically reserved resources.
    -   `add`: Adds one or more nodes to a cluster.
    -   `wait-for-service`: Waits for the Riak node to respond to pings, and then waits for it to be joined to the cluster.
-   `riak-mesos proxy`: Interact with the RMF smart proxy.
    -   `config`: Output the generated Marathon json application definition for the RMF smart proxy.
    -   `install`: Install the RMF smart proxy as a marathon app.
    -   `uninstall`: Delete the RMF smart proxy from Marathon.
    -   `endpoints`: List the endpoints and descriptions provided by the RMF smart proxy.
    -   `wait-for-service`: Waits for the proxy service to return OK.

Options (available on most commands):
    --config <json-file> (/etc/riak-mesos/config.json)
    --cluster <cluster-name> (default)
    --debug
    --help
    --info
    --version

Install the RMF
---------------

First, verify that your `/etc/riak-mesos/config.json` is getting processed correctly with:

```
riak-mesos config
```

Run the following command to create a Marathon application with the id `riak`

``` sourceCode
riak-mesos framework install
```

To make deployment scripting easier, use the `wait-for-service` command to block until the framework is ready for service:

``` sourceCode
riak-mesos framework wait-for-service
```

Create a cluster
----------------

Let's start with a 3 node cluster. First check if any clusters have already been created, and then verify the configuration:

```
riak-mesos cluster list
riak-mesos cluster config
riak-mesos cluster config advanced
```

Create the cluster object in the RMF metadata, and then instruct the scheduler to create 3 Riak nodes:

``` sourceCode
riak-mesos cluster create
riak-mesos node add --nodes 3
riak-mesos node list
```

After a few moments, we can verify that individual nodes are ready for service with:

```
riak-mesos node wait-for-service --node riak-default-1
riak-mesos node wait-for-service --node riak-default-2
riak-mesos node wait-for-service --node riak-default-3
```

Alternatively a shortcut to the above is:

```
riak-mesos cluster wait-for-service
```

To get connection information about each of the nodes directly, try this command:

```
riak-mesos cluster endpoints | python -m json.tool
```

The output should look similar to this:

```
{
    "riak-default-1": {
        "alive": true,
        "http_direct": "mesos-slave-01.novalocal:52041",
        "http_mesos_dns": "riak-default.riak.mesos:52041",
        "pb_direct": "mesos-slave-01.novalocal:52042",
        "pb_mesos_dns": "riak-default.riak.mesos:52042"
    },
    "riak-default-2": {
        "alive": true,
        "http_direct": "mesos-slave-01.novalocal:65397",
        "http_mesos_dns": "riak-default.riak.mesos:65397",
        "pb_direct": "mesos-slave-01.novalocal:65398",
        "pb_mesos_dns": "riak-default.riak.mesos:65398"
    },
    "riak-default-3": {
        "alive": true,
        "http_direct": "mesos-slave-01.novalocal:17907",
        "http_mesos_dns": "riak-default.riak.mesos:17907",
        "pb_direct": "mesos-slave-01.novalocal:17908",
        "pb_mesos_dns": "riak-default.riak.mesos:17908"
    }
}
```

Inspecting Nodes
----------------

Now that the cluster is running, let's perform some checks on individual nodes. This first command will show the hostname and ports for http and protobufs, as well as the metadata stored by the RMF:

```
riak-mesos node info --node riak-default-1
```

To get the current ring membership and partition ownership information for a node, try:

``` sourceCode
riak-mesos node status --node riak-default-1 | python -m json.tool
```

The output of that command should yield results similar to the following if everything went well:

``` sourceCode
{
    "down": 0,
    "exiting": 0,
    "joining": 0,
    "leaving": 0,
    "nodes": [
        {
            "id": "riak-default-1@mesos-slave-01.novalocal",
            "pending_percentage": null,
            "ring_percentage": 32.8125,
            "status": "valid"
        },
        {
            "id": "riak-default-2@mesos-slave-01.novalocal",
            "pending_percentage": null,
            "ring_percentage": 32.8125,
            "status": "valid"
        },
        {
            "id": "riak-default-3@mesos-slave-01.novalocal",
            "pending_percentage": null,
            "ring_percentage": 34.375,
            "status": "valid"
        }
    ],
    "valid": 3
}
```

Other useful information can be found by executing these commands:

``` sourceCode
riak-mesos node aae-status --node riak-default-1
riak-mesos node ringready --node riak-default-1
riak-mesos node transfers --node riak-default-1
```

Update the Cluster Configuration
--------------------------------

You can customize the `riak.conf` and `advanced.config` for a cluster if necessary. Use <https://github.com/basho-labs/riak-mesos/blob/master/artifacts/data/riak.erlang.conf> (or riak.golang.conf) and <https://github.com/basho-labs/riak-mesos/blob/master/artifacts/data/advanced.erlang.config> (or advanced.golang.conf) as templates to make your changes to. It is important that all of the values specified with `{{...}}` remain intact.

Once you have created your customized versions of these files, you can save them to the cluster using the following commands:

Update riak.conf
----------------

As an example, I've created a file called `riak.more_logging.conf` in which I've updated this line: `log.console.level = debug`

``` sourceCode
riak-mesos cluster config --file riak.more_logging.conf
```

Update advanced.config
----------------------

Similarly the advanced.config can be updated like so:

``` sourceCode
riak-mesos cluster config advanced --file /path/to/your/advanced.config
```

**Note:** If you already have nodes running in a cluster, you'll need to perform a `riak-mesos cluster restart` to force the cluster to pick up the new changes.

Restart the Cluster
-------------------

If your Riak cluster is in a stable state (no active transfers, ringready is true), there are certain situations where you might want to perform a rolling restart on your cluster. Execute the following to restart your cluster:

``` sourceCode
riak-mesos node ringready --node riak-default-1
riak-mesos node transfers --node riak-default-1
riak-mesos cluster restart
```

Situations where a cluster restart is required include:

-   Changes to `riak.conf`
-   Changes to `advanced.config`
-   Upgrading to a new version of RMF / Riak

Create Bucket Types
-------------------

Several newer features in Riak require the creation of bucket types. To see the current bucket types and their properties, use the following:

```
riak-mesos node bucket-type list --node riak-default-1 | python -m json.tool
```

Use this command to create a new bucket type with custom properties:

```
riak-mesos node bucket-type create --node riak-default-1 --bucket-type mytype --props '{"props":{"n_val": 3}}'
```

More information about specific bucket type properties can be found here: <http://docs.basho.com/riak/latest/dev/advanced/bucket-types/>.

A successful response looks like this:

```
{"mytype": {"actions": {"create": "mytype created", "activate": "mytype has been activated"}, "success": true}, "links": {"self": "/admin/explore/nodes/riak-default-1@mesos-slave-01.novalocal/bucket_types/mytype"}}
```

To update an existing type, just modify the command and run it again:

```
riak-mesos node bucket-type create --node riak-default-1 --bucket-type mytype --props '{"props":{"n_val": 2}}'
```

Which should give something like this back:

```
{"mytype": {"actions": {"update": "mytype updated"}, "success": true}, "links": {"self": "/admin/explore/nodes/riak-default-1@mesos-slave-01.novalocal/bucket_types/mytype"}}
```

Install the Proxy
-----------------

There are a few ways to access the Riak nodes in your cluster, including hosting your own HAProxy and keeping the config updated to include the host names and ports for all of the nodes. This approach can be problematic because the HAProxy config would need to be updated every time there is a change to one of the nodes in the cluster resulting from restarts, task failures, etc.

To account for this difficulty, we've created a smart proxy called the `riak-mesos-director`. The director should keep tabs on the current state of the cluster including all of the hostnames and ports, and it also provides a load balancer / proxy to spread load across all of the nodes.

To install the proxy as a marathon app with the id `riak-director`, simply run:

``` sourceCode
riak-mesos proxy install
```

Add Some Data
-------------

Assuming that the proxy is now running, we can now find an endpoint to talk to Riak with this command:

``` sourceCode
riak-mesos proxy endpoints
```

The output should look similar to this:

``` sourceCode
Load Balanced Riak Cluster (HTTP)
    http://SOME_AGENT_HOSTNAME:31026
Load Balanced Riak Cluster (Protobuf)
    http://SOME_AGENT_HOSTNAME:31027
Riak Mesos Director API (HTTP)
    http://SOME_AGENT_HOSTNAME:31028
```

Let's write a few keys to the cluster using the proxy:

``` sourceCode
RIAK_HTTP=http://SOME_AGENT_HOSTNAME:31026
curl -XPUT $RIAK_HTTP/buckets/test/keys/one -d "this is data"
curl -XPUT $RIAK_HTTP/buckets/test/keys/two -d "this is data too"
```

Scale up
--------

When scaling a cluster up, you should attempt to do so days or even weeks before the additional load is expected to allow the cluster some time to transfer partitions around and stabilize. When you are ready to increase the node count, you can just run the node add command like so:

``` sourceCode
riak-mesos node add
riak-mesos node wait-for-service --node riak-default-4
```

Check the status of the node and make sure it was successfully joined to the cluster using:

``` sourceCode
riak-mesos node status --node riak-default-4
```

Scale down
----------

Scaling down requires the same patience as scaling up in that you should be waiting for transfers to complete between each node removal.

Let's remove all but one of the nodes by performing a remove on `riak-default-2`, `riak-default-3`, and `riak-default-4`, verifying the data and node status after each step.

``` sourceCode
riak-mesos node remove --node riak-default-4
riak-mesos node status --node riak-default-1
curl $RIAK_HTTP/buckets/test/keys/one
```

``` sourceCode
riak-mesos node remove --node riak-default-3
riak-mesos node status --node riak-default-1
curl $RIAK_HTTP/buckets/test/keys/two
```

``` sourceCode
riak-mesos node remove --node riak-default-2
riak-mesos node status --node riak-default-1
curl $RIAK_HTTP/buckets/test/keys/one
curl $RIAK_HTTP/buckets/test/keys/two
```

Uninstall RMF
=============

The following commands can be used to remove part or all of the RMF.

DCOS Riak Uninstall
-------------------

Follow these steps to cleanly remove riak from a DCOS cluster:

``` sourceCode
dcos riak proxy uninstall
dcos riak cluster destroy
dcos riak framework clean-metadata
dcos package uninstall riak
```

Uninstall the Proxy
-------------------

To remove a RMF Director application instance from Marathon:

``` sourceCode
riak-mesos proxy uninstall
```

Destroy a Cluster
-----------------

To kill all of the Riak nodes in a cluster:

``` sourceCode
riak-mesos cluster destroy
```

Uninstall a framework instance
------------------------------

To remove a RMF application instance from Marathon:

``` sourceCode
riak-mesos framework uninstall
```

Kill all RMF Instances and Tasks
--------------------------------

``` sourceCode
riak-mesos framework teardown
```

Remove Zookeeper Metadata
-------------------------

To remove the `/riak/frameworks/FRAMEWORK_NAME` from Zookeeper:

``` sourceCode
riak-mesos framework clean-metadata
```

Remove the pip package
----------------------

To remove the riak-mesos pip package:

``` sourceCode
sudo pip uninstall riak-mesos
```
