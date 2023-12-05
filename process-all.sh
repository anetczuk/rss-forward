#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


# run tests in venv (it verifies required packages)
$SCRIPT_DIR/tools/installvenv.sh --no-prompt
$SCRIPT_DIR/venv/runtests.py

$SCRIPT_DIR/tools/checkall.sh


echo "processing completed"
