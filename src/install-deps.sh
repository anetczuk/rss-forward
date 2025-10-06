#!/bin/bash

set -eu

## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


# ## ensure required version of pip3
# pip3 install --upgrade 'pip>=18.0'


## install requirements
PIP_ARGS=""
if [[ $* == *--break-system-packages* ]]; then
    PIP_ARGS="--break-system-packages"
fi
pip3 install $PIP_ARGS -r "$SCRIPT_DIR/requirements.txt"


echo -e "\ninstallation done\n"
