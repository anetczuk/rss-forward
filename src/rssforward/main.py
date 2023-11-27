#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import sys
import logging
import time
import argparse
import toml

from rssforward import logger
from rssforward import DATA_DIR
from rssforward.rss.rssserver import RSSServerManager
from rssforward.rssmanager import RSSManager


_LOGGER = logging.getLogger(__name__)


def load_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return toml.load(f)
    except FileNotFoundError:
        _LOGGER.warning("could not load config file '%s' - using default configuration", config_path)
    return {}


def main():
    parser = argparse.ArgumentParser(description='RSS Forward')
    parser.add_argument('-c', '--config', action='store', required=False, default="", help='Path to TOML config file' )

    args = parser.parse_args()

    logger.configure()

    parameters = load_config( args.config )
    print( parameters )

    manager = RSSManager(parameters)
    manager.generateData()

    # async start of RSS server
    general_section = parameters.get("general", {})
    rss_port = general_section.get("port", 8080)
    refresh_time = general_section.get("refresh_time", 3600)

    server = RSSServerManager()
    server.port = rss_port
    server.start(DATA_DIR)

    # data generation main loop
    try:
        while True:
            # time.sleep( 10 )
            time.sleep(refresh_time)
            manager.generateData()

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")
        server.stop()
    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        server.stop()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
