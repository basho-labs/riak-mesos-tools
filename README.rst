Riak Mesos Tools
================
CLI and other tools for interacting with the Riak Mesos Framework.

.. image:: https://secure.travis-ci.org/basho-labs/riak-mesos-tools.svg
    :target: http://travis-ci.org/basho-labs/riak-mesos-tools

Requirements
------------
Before getting started with the RMF, there are a few environment and system related requirements that are assumed for the remainder of this tutorial:

* A Mesos cluster version 0.25.0.
* Python version 2.7 or above.
* Operating system is one of: Ubuntu 14.04+, CentOS 7.0+.

Note to DCOS Users
==================
All of the below instructions will work for the `dcos riak` command, just replace `riak-mesos` with `dcos riak`. Some other differences will be pointed out in the corresponding sections.

Installation
============

DCOS Install
------------
* Create a file at `/etc/riak-mesos/config.json` and use this `config.json <config/config.example.json>`_ as a template. More information on configuration values can be found below.
* Append the DCOS Riak package repo to your DCOS repo sources::

    dcos config prepend package.sources https://github.com/basho-labs/riak-mesos-dcos-repo/archive/0.3.1.zip

* Update packages::

    dcos package update

* Install the dcos riak subcommand::

    dcos package install riak --options /etc/riak-mesos/config.json


Pip Install
-----------
**Note:** You may need to run `pip uninstall riak-mesos` first to ensure the latest version.

.. code::

   pip install --upgrade git+https://github.com/basho-labs/riak-mesos-tools.git#egg=riak_mesos
   pip install --upgrade git+https://github.com/basho-labs/riak-mesos-tools.git@0.3.1#egg=riak_mesos

Quick Install
-------------
The included install.sh script will download and extract this package into $HOME/bin/riak-mesos-tools. Using this method does not require DCOS or pip or any of the other dependencies, and should work with most basic Python 2.7+ installations.

.. code::

   curl -s -L https://raw.githubusercontent.com/basho-labs/riak-mesos-tools/master/install.sh | sh

Create a Configuration File
---------------------------
If your environment differs from the required the default parameters, you may need to create a custom configuration file. Export the default config using this command:

.. code::

   riak-mesos config --json | python -m json.tool > config.json
   mv config.json /etc/riak-mesos/config.json

The resulting `/etc/riak-mesos/config.json` can then be modified to fit your environment. Here is a brief description of some of those values:

* **riak.url**: Location of the RMF tar ball which contains the actual RMF executables. Following are the current releases:
    * Ubuntu 14.04 with Golang Executor: **"http://riak-tools.s3.amazonaws.com/riak-mesos/golang/ubuntu/riak_mesos_linux_amd64_0.3.1.tar.gz"**
  * Ubuntu 14.04 with Erlang Executor (Mesos 0.26 Only): **"http://riak-tools.s3.amazonaws.com/riak-mesos/erlang/mesos-0.26/ubuntu/riak_mesos_linux_amd64_0.3.1.tar.gz"**
  * CentOS/RHEL 7 with Golang Executor: **"http://riak-tools.s3.amazonaws.com/riak-mesos/golang/centos/riak_mesos_linux_amd64_0.3.1.tar.gz"**
  * CentOS/RHEL 7 with Erlang Executor (Mesos 0.26 Only): **"http://riak-tools.s3.amazonaws.com/riak-mesos/erlang/mesos-0.26/centos/riak_mesos_linux_amd64_0.3.1.tar.gz"**
* **riak.master**: The address for the Mesos master. Example values:
  * **localhost:5050**
  * **leader.mesos:5050**
  * **zk://leader.mesos:2181/mesos**
* **riak.zk**: The address for Zookeeper. Default value is: **leader.mesos:2181**.
* **riak.cpus**: Amount of CPU resources for the Framework task. Default value is: **0.5**.
* **riak.mem**: Amount of Memory for the Framework task. Default value is: **2048**.
* **riak.node.cpus**: Amount of CPU resources per Riak node. Default value is: **1.0**.
* **riak.node.disk**: Amount of Memory resources per Riak node. Default value is: **8000**.
  * **Note:** To ensure that each Riak node resides on a unique Mesos agent / physical host, this value should be at least 51% of a single Mesos agent's total capacity.
* **riak.node.mem**: Amount of Disk resources per Riak node. Default value is: **20000**.
* **riak.role**: Mesos role for the RMF and tasks. Required for Dynamic Reservations / Persistent Volumes.
  * **Note:** The Mesos master may need to be restarted with **MESOS_ROLES=riak** or **--roles=riak**.
* **riak.user**: The user which will run the Riak process and executor. The user must exist on all of the Mesos agents, and **must not be root**.
* **riak.auth-principal**: The Mesos authentication principal. Required for Dynamic Reservations / Persistent Volumes.
* **riak.flags**: Any additional flags to pass to the RMF. Default value is: **"-use_reservations"**. Remove this parameter when running Mesos version 0.23 or lower.
* **director.url**: Location for the RMF smart proxy. The smart proxy will automatically detect changes in the Riak cluster topology based on updates to Zookeeper values stored by each of the running Riak nodes.
* **director.use-public**: When this is true, the smart proxy will only be deployed on an agent with a public role.
* **director.cmd**: Legacy versions of the framework may need to modify this.
* **marathon.url**: Address for Marathon. Default value is: **"http://marathon.mesos:8080"**.


Usage
=====
Try executing `riak-mesos`, `riak-mesos -h`, or `riak-mesos --help` to output the usage instructions.

We'll be covering the majority of the commands in this guide. Here is a brief description of some of them:

* `riak-mesos config`: Output the current configuration values.
* `riak-mesos framework`: Interact with the RMF application.
  * `config`: Output the generated Marathon json application definition for the RMF.
  * `install`: Install the RMF as a Marathon app.
  * `uninstall`: Delete the RMF from Marathon and delete related Zoookeeper entries.
    * **Note:** This will not kill Riak node tasks, so make sure to run `riak-mesos cluster destroy` first.
* `riak-mesos cluster`
  * `create`: Creates a named Riak cluster (default is `default`) in the RMF using default values for `riak.conf` and `advanced.config`.
  * `list`: Lists the names of each cluster.
  * `config`: Outputs the configuration values for `riak.conf` and `advanced.config`.
  * `restart`: Performs a rolling restart of the cluster. If you've upgraded to a new version of the RMF or Riak, restarting the cluster will push the new Riak version while preserving the data directories if you are using persistent volumes.
  * `destroy`: Kills all Riak node tasks for a cluster, deletes any created persistent volumes, and un-reserves any dynamically reserved resources for the nodes.
* `riak-mesos node`: Interact with an individual node in the cluster.
  * `info`: Outputs information about a Riak node stored by the RMF.
  * `aae-status`: Outputs the active anti entropy status for a node.
  * `status`: Outputs the member status information for a node.
  * `ringready`: Outputs the ringready status for a node.
  * `transfers`: Outputs the active and waiting partition transfers for a node.
  * `bucket-type`: Interact with bucket types on a node / cluster.
      * `create`: Creates and activates a bucket type given some properties as json.
      * `list`: List all bucket types and their properties from a node / cluster.
  * `list`: List all nodes in a cluster.
  * `remove`: Kills the task for a node, destroys any created persistent volumes, and un-reserves any dynamically reserved resources.
  * `add`: Adds one or more nodes to a cluster.
* `riak-mesos proxy`: Interact with the RMF smart proxy.
  * `config`: Output the generated Marathon json application definition for the RMF smart proxy.
  * `install`: Install the RMF smart proxy as a marathon app.
  * `uninstall`: Delete the RMF smart proxy from Marathon.
  * `endpoints`: List the endpoints and descriptions provided by the RMF smart proxy.

Install the RMF
---------------
Run the following command to create a Marathon application with the id `riak`:

.. code::

   riak-mesos framework install

You can check the status of the Marathon app deployment by navigating to [http://marathon.mesos:8080](http://marathon.mesos:8080) directly, or with this snippet:

.. code::

   curl --silent http://marathon.mesos:8080/v2/apps/riak | python -m json.tool | grep alive

Create a cluster
----------------
Let's start with a 3 node cluster. Execute the following to get started:

.. code::
   riak-mesos cluster create
   riak-mesos node add --nodes 3

After a few moments, we can check the status of our nodes:

.. code::

   riak-mesos node list --json | python -m json.tool | grep CurrentState

A status of `3` means that the nodes are in the `Started` state, so a healthy cluster would look like this:

.. code::

   "CurrentState": 3,
   "CurrentState": 3,
   "CurrentState": 3,

Inspecting Nodes
----------------
Now that the cluster is running, let's perform some checks on individual nodes.

.. code::

   riak-mesos node status --node riak-default-1 | python -m json.tool

The output of that command should yield results similar to the following if everything went well:

.. code::

    "nodes": [
        {
            "id": "riak-default-1@ip-172-31-51-148.ec2.internal",
            "pending_percentage": null,
            "ring_percentage": 34.375,
            "status": "valid"
        },
        {
            "id": "riak-default-2@ip-172-31-51-148.ec2.internal",
            "pending_percentage": null,
            "ring_percentage": 32.8125,
            "status": "valid"
        },
        {
            "id": "riak-default-3@ip-172-31-51-148.ec2.internal",
            "pending_percentage": null,
            "ring_percentage": 32.8125,
            "status": "valid"
        }
    ],
    "valid": 3

Other useful information can be found by executing these commands:

.. code::

   riak-mesos node aae-status --node riak-default-1
   riak-mesos node ringready --node riak-default-1
   riak-mesos node transfers --node riak-default-1

Update the Cluster Configuration
--------------------------------
You can customize the `riak.conf` and `advanced.config` for a cluster if necessary. Use [scheduler/data/riak.conf](https://github.com/basho-labs/riak-mesos/blob/master/scheduler/data/riak.conf) and [scheduler/data/advanced.config](https://github.com/basho-labs/riak-mesos/blob/master/scheduler/data/advanced.config) as templates to make your changes to. It is important that all of the values specified with `{{...}}` remain intact.

Once you have created your customized versions of these files, you can save them to the cluster using the following commands:

Update riak.conf
----------------
.. code::

   riak-mesos cluster config --file /path/to/your/riak.conf

Update advanced.config
----------------------
.. code::

   riak-mesos cluster config advanced --file /path/to/your/advanced.config

**Note:** If you already have nodes running in a cluster, you'll need to perform a `riak-mesos cluster restart` to force the cluster to pick up the new changes.

Restart the Cluster
-------------------
If your Riak cluster is in a stable state (no active transfers, ringready is true), there are certain situations where you might want to perform a rolling restart on your cluster. Execute the following to restart your cluster:

.. code::

   riak-mesos cluster restart

Situations where a cluster restart is required include:

* Changes to `riak.conf`
* Changes to `advanced.config`
* Upgrading to a new version of RMF / Riak

Install the Proxy
-----------------
There are a few ways to access the Riak nodes in your cluster, including hosting your own HAProxy and keeping the config updated to include the host names and ports for all of the nodes. This approach can be problematic because the HAProxy config would need to be updated every time there is a change to one of the nodes in the cluster resulting from restarts, task failures, etc.

To account for this difficulty, we've created a smart proxy called `riak mesos director`. The director should keep tabs on the current state of the cluster including all of the hostnames and ports, and it also provides a load balancer / proxy to spread load across all of the nodes.

To install the proxy, simply run:

.. code::

   riak-mesos proxy install

Add Some Data
-------------
Assuming that the proxy is now running, we can now find an endpoint to talk to Riak with this command:

.. code::

   riak-mesos proxy endpoints

The output should look similar to this:

.. code::

   Load Balanced Riak Cluster (HTTP)
       http://SOME_AGENT_HOSTNAME:31026
   Load Balanced Riak Cluster (Protobuf)
       http://SOME_AGENT_HOSTNAME:31027
   Riak Mesos Director API (HTTP)
       http://SOME_AGENT_HOSTNAME:31028

Let's write a few keys to the cluster using the proxy:

.. code::

   RIAK_HTTP=http://SOME_AGENT_HOSTNAME:31026
   curl -XPUT $RIAK_HTTP/buckets/test/keys/one -d "this is data"
   curl -XPUT $RIAK_HTTP/buckets/test/keys/two -d "this is data too"

Scale up
--------
When scaling a cluster up, you should attempt to do so days or even weeks before the additional load is expected to allow the cluster some time to transfer partitions around and stabilize. When you are ready to increase the node count, you can just run the `node add` command like so:

.. code::

   riak-mesos node add

Check the status of the node and make sure it was successfully joined to the cluster using:

.. code::

   riak-mesos node status --node riak-default-4

Scale down
----------
Scaling down requires the same patience as scaling up in that you should be waiting for transfers to complete between each node removal.

Let's remove all but one of the nodes by performing a remove on `riak-default-2`, `riak-default-3`, and `riak-default-4`

.. code::

   riak-mesos node remove --node riak-default-2
   riak-mesos node remove --node riak-default-3
   riak-mesos node remove --node riak-default-4

Verify the Data
---------------
Now that the cluster has undergone some changes, lets verify the data that was written previously with:

.. code::

   curl $RIAK_HTTP/buckets/test/keys/one
   curl $RIAK_HTTP/buckets/test/keys/two

Uninstall RMF
=============

The following tasks can be used depending on the end goal.

DCOS Riak Uninstall
-------------------

Follow these steps to cleanly remove riak from a DCOS cluster:

.. code::

   dcos riak proxy uninstall
   dcos riak cluster destroy
   dcos riak framework clean-metadata
   dcos package uninstall riak

Uninstall the Proxy
-------------------
To remove a RMF Director application instance from Marathon:

.. code::

   riak-mesos proxy uninstall

Destroy a Cluster
-----------------
To kill all of the Riak nodes in a cluster:

.. code::

   riak-mesos cluster destroy

Uninstall a framework instance
------------------------------
To remove a RMF application instance from Marathon:

.. code::

   riak-mesos framework uninstall

Kill all RMF Instances and Tasks
--------------------------------
.. code::

   riak-mesos framework teardown

Remove Zookeeper Metadata
-------------------------
To remove the `/riak/frameworks/FRAMEWORK_NAME` from Zookeeper:

.. code::

   riak-mesos framework clean-metadata

Remove the pip package
----------------------
To remove the riak-mesos pip package:

.. code::

   pip uninstall riak-mesos
