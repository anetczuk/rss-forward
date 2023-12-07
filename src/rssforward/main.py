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

from rssforward import logger
from rssforward.rss.rssserver import RSSServerManager
from rssforward.rssmanager import RSSManager
from rssforward.configfile import load_config, ConfigField, ConfigKey


_LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="RSS Forward")
    parser.add_argument("-c", "--config", action="store", required=False, default="", help="Path to TOML config file")
    parser.add_argument(
        "--no-server",
        action="store_true",
        required=False,
        help="Do not run RSS server (overrides config 'startserver' option)",
    )

    args = parser.parse_args()

    logger.configure()

    parameters = load_config(args.config)

    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    data_root = general_section.get(ConfigField.DATAROOT.value)
    _LOGGER.info("RSS data root dir: %s", data_root)

    manager = RSSManager(parameters)
    manager.generateData()

    # async start of RSS server
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)
    start_server = general_section.get(ConfigField.STARTSERVER.value, True)

    if args.no_server:
        start_server = False

    rss_server: RSSServerManager = None
    if start_server:
        rss_port = general_section.get(ConfigField.PORT.value, 8080)
        rss_server = RSSServerManager()
        rss_server.port = rss_port
        rss_server.start(data_root)
    else:
        _LOGGER.info("starting RSS server disabled")

    # data generation main loop
    try:
        while True:
            # time.sleep( 10 )
            _LOGGER.info("waiting %s seconds before next fetch", refresh_time)
            time.sleep(refresh_time)
            manager.generateData()

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")
        if rss_server:
            rss_server.stop()
    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        if rss_server:
            rss_server.stop()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
