# Riak Mesos CLI / DC/OS Riak


CLI and other tools for interacting with the Riak Mesos Framework.

[![image](https://secure.travis-ci.org/basho-labs/riak-mesos-tools.svg)](http://travis-ci.org/basho-labs/riak-mesos-tools)

-------------
## Requirements


Before getting started with the RMF, there are a few environment and system related requirements that are assumed for the remainder of this tutorial:

-   A Mesos cluster version 1.0.x or above
-   Python version 2.7 or above.
-   One of the currently supported operating systems. Check the [configuration](#create-a-configuration-file) section for more information.


### Note to DC/OS and DC/OS CLI Users


All of the below instructions will work for the `dcos riak` command, just replace `riak-mesos` with `dcos riak`. Some other differences will be pointed out in the corresponding sections.

------------------

## Installation


### Pip Install


### Install the latest tag

- Install the latest version:

        sudo pip install --upgrade git+https://github.com/basho-labs/riak-mesos-tools.git@riak-mesos-v1.1.x#egg=riak_mesos

### DC/OS CLI v0.4.x Install

-   [Create a Configuration File](#create-a-configuration-file) and store it in `/etc/riak-mesos/config.json`
- Add the DC/OS Riak package to your DC/OS repository sources:

		dcos package repo add --index=0 Riak https://github.com/basho-labs/riak-mesos-dcos-repo/archive/2.0.0.zip

	NB: the `--index=0` argument is required for the Riak package to show up in `dcos package search riak`

- Install the `dcos riak` subcommand:

		dcos package install riak --options /etc/riak-mesos/config.json

    NB: the `--options foo.json` argument must come AFTER the package name, or dcos will silently ignore it.

Create a Configuration File
---------------------------

- Copy the contents of [config.example.json](config/config.example.json) ([config.dcos.json](config/config.dcos.json) for DC/OS users) into a local file at the path `/etc/riak-mesos/config.json`:

		mkdir -p /etc/riak-mesos
		curl https://raw.githubusercontent.com/basho-labs/riak-mesos-tools/riak-mesos-v1.1.x/config/config.example.json > /etc/riak-mesos/config.json

- Inspect the resulting `/etc/riak-mesos/config.json` and make changes to parameters according to your system requirements. For more information on each of the configuration values, please see [this schema file](https://raw.githubusercontent.com/basho-labs/riak-mesos-dcos-repo/2.0.0/repo/packages/R/riak/2/config.json) for field descriptions.

- The example config files expect an environment based on mesos-1.0.1 running on ubuntu-14.04. Change the various `url` and `package` fields to point to the relevant artifacts for your mesos and OS setup, or to switch to Riak TS. Available packages for each corresponding configuration item are located as follows:
    - `resources.scheduler`: [riak-mesos-scheduler/releases](https://github.com/basho-labs/riak-mesos-scheduler/releases)
    - `resources.executor`: [riak-mesos-executor/releases](https://github.com/basho-labs/riak-mesos-executor/releases)
    - `resources.patches`: [riak-mesos-executor/releases](https://github.com/basho-labs/riak-mesos-executor/releases)
    - `resources.explorer`: [riak_explorer/releases](https://github.com/basho-labs/riak_explorer/releases)
    - `resources.director`: [riak-mesos-director/releases](https://github.com/basho-labs/riak-mesos-director/releases)

Usage
=====

Try executing `riak-mesos`, `riak-mesos -h`, or `riak-mesos --help` to output the usage instructions like so:

```
riak-mesos --help

Usage: riak-mesos [OPTIONS] COMMAND [ARGS]...

  Command line utility for the Riak Mesos Framework / DCOS Service. This
  utility provides tools for modifying and accessing your Riak on Mesos
  installation.

Options:
  --home DIRECTORY  Changes the folder to operate on.
  --config PATH     Path to JSON configuration file.
  -v, --verbose     Enables verbose mode.
  --debug           Enables very verbose / debug mode.
  --info            Display information.
  --version         Display version.
  --config-schema   Display config schema.
  --framework TEXT  Changes the framework instance to operate on.
  --json            Enables json output.
  --insecure-ssl    Turns SSL verification off on HTTP requests
  --help            Show this message and exit.

Commands:
  cluster    Interact with Riak clusters
  config     Interact with configuration.
  director   Interact with an instance of Riak Mesos...
  framework  Interact with an instance of Riak Mesos...
  node       Interact with a Riak node
  riak       Command line utility for the Riak Mesos...
```

To get information about a sub-command, try `riak-mesos <command> --help`:

```
riak-mesos cluster --help
Usage: riak-mesos cluster [OPTIONS] COMMAND [ARGS]...

  Interact with Riak clusters

...

Commands:
  add-node          Adds one or more (using --nodes) nodes.
  config            Gets or sets the riak.conf configuration for...
  config-advanced   Gets or sets the advanced.config...
  create            Creates a new cluster.
  destroy           Destroys a cluster.
  endpoints         Iterates over all nodes in cluster and prints...
  info              Gets current metadata about a cluster.
  list              Retrieves a list of clusters
  restart           Performs a rolling restart on a cluster.
  set               Sets list of clusters
  wait-for-service  Iterates over all nodes in cluster and...
```

Install the RMF
---------------

**NOTE:** This step is unecessary for DC/OS users since the `dcos package install` automatically performs this step.

Run the following command to create a Marathon application with an id that matches the `riak.framework-name` configuration value:

    riak-mesos framework install

To make deployment scripting easier, use the `wait-for-service` command to block until the framework is ready for service:

    riak-mesos framework wait-for-service

Create a cluster
----------------

Let's start with a 3 node cluster. First check if any clusters have already been created, and check available Riak versions:

    riak-mesos cluster list
    riak-mesos config riak-versions

Create the cluster object in the RMF metadata, and then instruct the scheduler to create 3 Riak nodes:

    riak-mesos cluster create ts riak-ts-1-4
    riak-mesos cluster add-node ts --nodes 3
    riak-mesos cluster list

After a few moments, we can verify that individual nodes are ready for service with:

    riak-mesos node wait-for-service riak-ts-1
    riak-mesos node wait-for-service riak-ts-2
    riak-mesos node wait-for-service riak-ts-3

Alternatively a shortcut to the above is:

    riak-mesos cluster wait-for-service ts

To get connection information about each of the nodes directly, try this command:

    riak-mesos cluster endpoints ts | python -m json.tool

The output should look similar to this:

```
{
    "riak-ts-1": {
        "alive": true,
        "http_direct": "mesos-agent-1.com:31716",
        "pb_direct": "mesos-agent-1.com:31717",
        "status": "started"
    },
    "riak-ts-2": {
        "alive": true,
        "http_direct": "mesos-agent-2.com:31589",
        "pb_direct": "mesos-agent-2.com:31590",
        "status": "started"
    },
    "riak-ts-3": {
        "alive": true,
        "http_direct": "mesos-agent-3.com:31491",
        "pb_direct": "mesos-agent-3.com:31492",
        "status": "started"
    }
}
```

Inspecting Nodes
----------------

Now that the cluster is running, let's perform some checks on individual nodes. This first command will show the hostname and ports for http and protobufs, as well as the metadata stored by the RMF:

    riak-mesos node info riak-ts-1

To get the current ring membership and partition ownership information for a node, try:

    riak-mesos node status riak-ts-1 | python -m json.tool

The output of that command should yield results similar to the following if everything went well:

``` sourceCode
{
    "down": 0,
    "exiting": 0,
    "joining": 0,
    "leaving": 0,
    "nodes": [
        {
            "id": "riak-ts-1@ubuntu.local",
            "pending_percentage": null,
            "ring_percentage": 32.8125,
            "status": "valid"
        },
        {
            "id":  "riak-ts-2@ubuntu.local",
            "pending_percentage": null,
            "ring_percentage": 32.8125,
            "status": "valid"
        },
        {
            "id": "riak-ts-3@ubuntu.local",
            "pending_percentage": null,
            "ring_percentage": 34.375,
            "status": "valid"
        }
    ],
    "valid": 3
}
```

Other useful information can be found by executing these commands:

    riak-mesos node aae-status riak-ts-1
    riak-mesos node ringready riak-ts-1
    riak-mesos node transfers riak-ts-1

Cluster Configuration
---------------------

By default, the Riak-Mesos Framework will use the config file that ships with the Riak archive you install, plus some automated modifications. However, you can customize the `riak.conf` and `advanced.config` for a cluster if necessary. Use [riak-mesos/master/docs/riak.conf.default](https://raw.githubusercontent.com/basho-labs/riak-mesos/master/docs/riak.conf.default) and [riak-mesos/master/docs/advanced.config.default](https://raw.githubusercontent.com/basho-labs/riak-mesos/master/docs/advanced.config.default) as templates.

It is important to note that [certain configuration items](#executor-config-template-variables) cannot be customised. Their values are controlled by the executor, as is required to allow operation within Mesos.

Once you have created your customized versions of these files, you can save them to the cluster using the following commands:

Update riak.conf
----------------

As an example, I've created a file called `riak.more_logging.conf` in which I've updated this line: `log.console.level = debug`

    riak-mesos cluster config ts --file riak.more_logging.conf

Update advanced.config
----------------------

Similarly the advanced.config can be updated like so:

    riak-mesos cluster config-advanced ts --file /path/to/your/advanced.config

**Note:** If you already have nodes running in a cluster, you'll need to perform a `riak-mesos cluster restart` to force the cluster to pick up the new changes.

Executor Config Template Variables
----------------------------------

The following template variables are used when modifying the Riak config template, upon creating a node in a cluster:

| Variable                 | Meaning             |
| ------------------------ | ------------------- |
| `fullyqualifiednodename` | Riak nodename       |
| `handoffport`            | Handoff Port        |
| `disterlport`            | Erlang distribution |
| `httpport`               | HTTP Port           |
| `pbport`                 | Protobuf Port       |
| `cepmdport`              | EPMD Port           |
| `data_dir`               | Riak Data dir       |
| `bindaddress`            | Network bind addr   |


Restart the Cluster
-------------------

If your Riak cluster is in a stable state (no active transfers, ringready is true), there are certain situations where you might want to perform a rolling restart on your cluster. Execute the following to restart your cluster:

    riak-mesos node ringready riak-ts-1
    riak-mesos node transfers riak-ts-1 --wait-for-service
    riak-mesos cluster restart ts

Situations where a cluster restart is required include:

-   Changes to `riak.conf`
-   Changes to `advanced.config`
-   Upgrading to a new version of RMF scheduler or any of the other artifacts
-   Upgrading to a new version of Riak

Create Bucket Types
-------------------

Several newer features in Riak require the creation of bucket types. To see the current bucket types and their properties, use the following:

    riak-mesos node bucket-type list riak-ts-1 | python -m json.tool

Use this command to create a new bucket type with custom properties:

    riak-mesos node bucket-type create riak-ts-1 mytype '{"props":{"n_val": 3}}'

More information about specific bucket type properties can be found here: <http://docs.basho.com/riak/latest/dev/advanced/bucket-types/>.

A successful response looks like this:

    {"mytype":{"success":true,"actions":{"create":"mytype created","activate":"mytype has been activated"}}}

To update an existing type, just modify the command and run it again:

    riak-mesos node bucket-type update riak-ts-1 mytype '{"props":{"n_val": 2}}'

Which should give something like this back:

    {"mytype":{"success":true,"actions":{"update":"mytype updated"}}}

Install the Director
-----------------

There are a few ways to access the Riak nodes in your cluster, including hosting your own HAProxy and keeping the config updated to include the host names and ports for all of the nodes. This approach can be problematic because the HAProxy config would need to be updated every time there is a change to one of the nodes in the cluster resulting from restarts, task failures, etc.

To account for this difficulty, we've created a smart proxy called the `riak-mesos-director`. The director should keep tabs on the current state of the cluster including all of the hostnames and ports, and it also provides a load balancer / proxy to spread load across all of the nodes.

To install the director as a marathon app with an id that matches your configured cluster name (default is `default`) + `-director`, simply run:

    riak-mesos director install

Add Some Data
-------------

Assuming that the director is now running, we can now find an endpoint to talk to Riak with this command:

    riak-mesos director endpoints

The output should look similar to this:

```
{
    "cluster": "default",
    "director_http": "mesos-agent-4.com:31694",
    "framework": "riak",
    "riak_http": "mesos-agent-4.com:31692",
    "riak_pb": "mesos-agent-4.com:31693"
}
```

Let's write a few keys to the cluster using the director:

    RIAK_HTTP=$(riak-mesos director endpoints | python -c 'import sys, json; print json.load(sys.stdin)["riak_http"]')
    curl -XPUT $RIAK_HTTP/buckets/test/keys/one -d "this is data"
    curl -XPUT $RIAK_HTTP/buckets/test/keys/two -d "this is data too"

Scale up
--------

When scaling a cluster up, you should attempt to do so days or even weeks before the additional load is expected to allow the cluster some time to transfer partitions around and stabilize. When you are ready to increase the node count, you can just run the node add command like so:

    riak-mesos node add
    riak-mesos node wait-for-service --node riak-default-4
    riak-mesos node transfers wait-for-service --node riak-default-4

Check the status of the node and make sure it was successfully joined to the cluster using:

    riak-mesos node status --node riak-default-4

Scale down
----------

Scaling down requires the same patience as scaling up in that you should be waiting for transfers to complete between each node removal.

Let's remove all but one of the nodes by performing a remove on `riak-default-2`, `riak-default-3`, and `riak-default-4`, verifying the data and node status after each step.

    riak-mesos node remove --node riak-default-4
    riak-mesos node transfers wait-for-service --node riak-default-1
    curl $RIAK_HTTP/buckets/test/keys/one


    riak-mesos node remove --node riak-default-3
    riak-mesos node transfers wait-for-service --node riak-default-1
    curl $RIAK_HTTP/buckets/test/keys/two


    riak-mesos node remove --node riak-default-2
    riak-mesos node transfers wait-for-service --node riak-default-1
    curl $RIAK_HTTP/buckets/test/keys/one
    curl $RIAK_HTTP/buckets/test/keys/two

Uninstall RMF
=============

The following commands can be used to remove part or all of the RMF.

- Uninstall the Director

        riak-mesos director uninstall

- Destroy Clusters

        riak-mesos cluster destroy

- Uninstall a framework instance

        riak-mesos framework uninstall

- Kill all RMF Instances and Tasks

        riak-mesos framework teardown

- Remove the pip package

        sudo pip uninstall riak-mesos

DC/OS Riak Uninstall
-------------------

Follow these steps to cleanly remove riak from a DC/OS cluster:

    dcos riak director uninstall
    dcos riak cluster destroy
    dcos package uninstall riak
