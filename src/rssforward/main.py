#!/usr/bin/python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
import time

from rssforward import logger
from rssforward import DATA_DIR
from rssforward.rss.rssserver import RSSServerManager
from rssforward.rssmanager import RSSManager


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure()

    manager = RSSManager()
    manager.generate_data()

    # async start of RSS server
    server = RSSServerManager()
    server.port = 8080
    server.start(DATA_DIR)

    # data generation main loop
    try:
        while True:
            # time.sleep( 10 )
            time.sleep( 60 * 60 )     # generate data every 1h
            manager.generate_data()

    except KeyboardInterrupt:
        _LOGGER.info("stopping the server")
        server.stop()

    return 0


if __name__ == "__main__":
    main()
