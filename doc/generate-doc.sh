#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


SRC_DIR="$SCRIPT_DIR/../src"


generate_help() {
    echo "generating help output"

    HELP_PATH=$SCRIPT_DIR/cmdargs.md
    
    echo "## rssforward.py --help" > ${HELP_PATH}
    echo -e "\`\`\`" >> ${HELP_PATH}
    $SRC_DIR/rssforward.py --help >> ${HELP_PATH}
    echo -e "\`\`\`" >> ${HELP_PATH}
}


generate_help


$SCRIPT_DIR/generate_small.sh
