#!/bin/bash

mkdir -p $HOME/bin
cd $HOME/bin && curl -sL https://github.com/basho-labs/riak-mesos-tools/archive/master.tar.gz | tar xz
mv master riak-mesos-tools

echo ""
echo "riak-mesos-tools installed to $HOME/bin/riak-mesos-tools"
echo ""
echo "Add riak-mesos to your path with:"
echo '    export PATH=$HOME/bin/riak-mesos-tools/bin:$PATH'
echo "Create a configuration file with:"
echo '    sudo mkdir -p /etc/riak-mesos'
echo '    sudo cp $HOME/bin/riak-mesos-tools/config/config.example.json /etc/riak-mesos/config.json'
