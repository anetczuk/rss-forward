#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


cd "$SCRIPT_DIR"


./codecheck.sh

echo
echo
./doccheck.sh

./typecheck.sh

echo
echo
./mdcheck.sh


echo
echo "everything is fine"
