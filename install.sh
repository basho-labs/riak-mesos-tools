#!/bin/bash

mkdir -p $HOME/bin
cd $HOME/bin && curl -O http://riak-tools.s3.amazonaws.com/riak-mesos/riak-mesos-cli-0.3.0.tar.gz
tar xvzf riak-mesos-cli-0.3.0.tar.gz

echo ""
echo "riak-mesos-cli installed to $HOME/bin/riak-mesos-cli"
echo ""
echo "Add riak-mesos to your path with:"
echo '    export PATH=$HOME/bin/riak-mesos-cli/bin:$PATH'
echo "Create a configuration file with:"
echo '    sudo mkdir -p /etc/riak-mesos'
echo '    sudo cp $HOME/bin/riak-mesos-cli/config/config.example.json /etc/riak-mesos/config.json'
