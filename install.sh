#!/bin/bash

mkdir -p $HOME/bin
cd $HOME/bin && curl -O https://github.com/basho-labs/riak-mesos-tools/archive/version-0.x.tar.gz riak-mesos-tools-version-0.x.tar.gz
tar xvzf riak-mesos-tools-0.3.0.tar.gz riak-mesos-tools
mv riak-mesos-tools-0.3.0 riak-mesos-tools

echo ""
echo "riak-mesos-tools installed to $HOME/bin/riak-mesos-tools"
echo ""
echo "Add riak-mesos to your path with:"
echo '    export PATH=$HOME/bin/riak-mesos-tools/bin:$PATH'
echo "Create a configuration file with:"
echo '    sudo mkdir -p /etc/riak-mesos'
echo '    sudo cp $HOME/bin/riak-mesos-tools/config/config.example.json /etc/riak-mesos/config.json'
