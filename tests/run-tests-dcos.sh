#!/bin/bash

# This script can be run under Docker like this, from the top-level riak-mesos-tools directory,
# given a config file with proper URLs for artifacts:
#
# docker run --rm -t -v $HOME/.dcos/dcos.toml:/tmp/dcos.toml \
# -v $(pwd)/tests/run-tests-dcos.sh:/root/run-tests-dcos.sh -v $(pwd):/tmp/riak-mesos-tools \
# basho/build-essential-mesos:ubuntu-14.04 /root/run-tests-dcos.sh

mkdir -p /root/.dcos

# Because Docker has issues placing files in directories that don't
# exist using volumes, copy it in place
if [ -e /tmp/dcos.toml ]; then
    cp /tmp/dcos.toml /root/.dcos
fi

pip install virtualenv

curl https://downloads.dcos.io/binaries/cli/linux/x86-64/dcos-1.8/dcos -o dcos &&
    sudo mv dcos /usr/local/bin &&
    sudo chmod +x /usr/local/bin/dcos
# TODO vv Change this back to 'develop.zip' vv
dcos package repo add Riak https://github.com/basho-labs/riak-mesos-dcos-repo/archive/mtc-th-dcos-tests-fixup.zip --index 0

git config --global --unset-all 'url.ssh://git@github.com.insteadof'
git config --global --unset-all 'url.ssh://git@github.com/.insteadof'

dcos --log-level=ERROR package install riak-ts --yes # --cli
dcos riak-ts framework wait-for-service --timeout 1000000

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
export RIAK_MESOS_CMD='dcos riak-ts --verbose'
make test-end-to-end
find . -name "end-to-end.html" -exec cp \{} /tmp/riak-mesos-tools \;
