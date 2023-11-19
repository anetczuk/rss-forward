#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


cd $SCRIPT_DIR


./codecheck.sh
./doccheck.sh
./typecheck.sh

echo "checking links in MD files"
./md_check_links.py -d ..


echo "everything is fine"
