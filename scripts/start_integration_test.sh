#!/bin/bash

# Clean and recreate environment
cd /riak-mesos
make clean env

# Activate the virtual environment so that we can run make
source env/bin/activate

# Run the default target: E.g. test and packages
make
