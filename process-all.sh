#!/bin/bash

##
## Run all tests and code check tool.
## Pass --release to use fresh venv installation.
##

set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


print_usage() {
    SCRIPT_NAME=$(basename "$(readlink -f "$0")")

    echo "${SCRIPT_NAME} [-h] [-n] [-r]"
    echo
    echo "prepare project in virtual environment, generate content, run tests and static analysis tools"
    echo
    echo "parameters:"
    echo "    -h|--help      this message"
    echo "    -n|--new       create new virtual environment even if one already exists"
    echo "    -r|--release   check project in *release* mode (as close to use case and independent from development as possible)"
}


ARGS=()
RELEASE_RUN=false
NEW_VENV=false

while :; do
    if [ -z "${1+x}" ]; then
        ## end of arguments (prevents unbound argument error)
        break
    fi

    case "$1" in
      -h|--help)         print_usage
                         exit 0
                         ;;

      -r|--release)      RELEASE_RUN=true 
                         shift ;;

      -n|--new)          NEW_VENV=true 
                         shift ;;

      *)  ARGS+=("$1")
          shift ;;
    esac
done


VENV_NAME="venv"
VENV_DIR="$SCRIPT_DIR/${VENV_NAME}"

ACTIVATE_VENV_PATH="$VENV_DIR/activatevenv.sh"


if [ "$RELEASE_RUN" = false ]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
    if [ ! -x "$PYTHON_BIN" ] || [ "$NEW_VENV" = true ]; then
        ## install venv
        echo "Preparing virtual environment"
        "$SCRIPT_DIR"/tools/installvenv.sh --dev --no-prompt "../${VENV_NAME}"
    else
        echo "Skipping venv installation"
        echo
    fi
else
    VENV_NAME=".venv_release"
    VENV_DIR="$SCRIPT_DIR/${VENV_NAME}"

    ACTIVATE_VENV_PATH="$VENV_DIR/activatevenv.sh"

    "$SCRIPT_DIR"/tools/installvenv.sh --no-prompt "../${VENV_NAME}"

    ## install development tools (e.g. for static code checks)
    $ACTIVATE_VENV_PATH "${SCRIPT_DIR}/tools/install-deps.sh --dev"
fi


# run tests in venv (it verifies required packages)
echo
echo "running tests"
for testscript in "${VENV_DIR}"/runtests*.sh; do
    if [[ -f "${testscript}" ]]; then
        "${testscript}"
    fi
done


if [ -f "$SCRIPT_DIR/doc/generate-doc.sh" ]; then
    echo "generating docs"
    $ACTIVATE_VENV_PATH "$SCRIPT_DIR"/doc/generate-doc.sh
fi

if [ -f "$SCRIPT_DIR/examples/generate-all.sh" ]; then
    echo "generating examples results"
    "$SCRIPT_DIR"/examples/generate-all.sh --venv
fi

echo
echo
echo "preparing README.md file"
$ACTIVATE_VENV_PATH "$SCRIPT_DIR"/tools/mdpreproc.py "$SCRIPT_DIR/README.md"


echo
echo
echo "Checking code"
$ACTIVATE_VENV_PATH "$SCRIPT_DIR/tools/checkall.sh"


echo
echo "Processing completed"
