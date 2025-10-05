#!/bin/bash


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


EXEC_PATH="$SCRIPT_DIR/startrssforward.py"
TOML_CONFIG_PATH=""

ARGS=()

while :; do
    if [ -z "${1+x}" ]; then
        ## end of arguments (prevents unbound argument error)
        break
    fi

    case "$1" in
      --exeprefix)      ## add prefix program
                        EXEC_PATH="$2 $EXEC_PATH"
                        shift; shift ;;
      --config)         ## add prefix program
                        TOML_CONFIG_PATH=$(realpath "$2")
                        shift; shift ;;
      *)  ARGS+=("${1}")
          shift ;;
    esac
done


## add udev rule
CONFIG_FILE=~/.local/share/applications/menulibre-rssforward.desktop


if [ "$TOML_CONFIG_PATH" != "" ]; then
    EXEC_PATH="$EXEC_PATH -c $TOML_CONFIG_PATH"
else
    echo "missing --config param"
    echo "please provide toml config path"
    exit 1
fi


cat > $CONFIG_FILE << EOL
[Desktop Entry]
Name=RSS Forward
GenericName=RSS Forward
Comment=Scrap data from web and provide as RSS feed.
Version=1.1
Type=Application
Exec=$EXEC_PATH
Path=$SCRIPT_DIR
Icon=$SCRIPT_DIR/rssforward/systray/rss-forward-blue-64.png
Actions=
Categories=Office;
StartupNotify=true
Terminal=false

EOL


echo "File created in: $CONFIG_FILE"
