#!/bin/bash

# This script can be run under Docker like this, from the top-level riak-mesos-tools directory,
# given a config file with proper URLs for artifacts:
#
# docker run --rm -t --dns <MESOS_DNS> -v $(pwd)/config.json:/tmp/config.json \
# -v $(pwd)/tests/run-tests.sh:/root/run-tests.sh -v $(pwd):/tmp/riak-mesos-tools \
# basho/build-essential-mesos:14.04-0.26 /root/run-tests.sh
#
# TODO Once artifacts are publicly published, add option to run this without an external
#      config file, use a standard config file (using Riak KV OSS, of course)

mkdir -p /etc/riak-mesos

# Because Docker has issues placing files in directories that don't
# exist using volumes, copy it in place
if [ -e /tmp/config.json ]; then
    cp /tmp/config.json /etc/riak-mesos
fi

apt-get install -y python-pip
cd /root

# Local copies of test code can be mounted as a volume
# But since the build process tries doing hard links, it doesn't work
# as a volume, so copy it into place
if [ -d /tmp/riak-mesos-tools ]; then
    cp -ar /tmp/riak-mesos-tools /root
# If none is mounted, check out from git
else
   git clone --depth 1 https://github.com/basho-labs/riak-mesos-tools.git
fi

cd riak-mesos-tools
make test-end-to-end
find . -name "end-to-end.html" -exec cp \{} /tmp/riak-mesos-tools \;
