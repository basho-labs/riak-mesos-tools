#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR
$BASEDIR/env/bin/tox -e py27-end-to-end

