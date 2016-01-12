#!/bin/bash

# Clean and recreate environment
make clean env

# Activate the virtual environment so that we can run make
source env/bin/activate

# Run the default target: E.g. test and packages
make
