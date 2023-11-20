#!/usr/bin/python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging

from rssforward import logger
from rssforward import DATA_DIR
from rssforward.rss.rssserver import RSSServerManager

from rssforward.site.librus import generate_feed


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure()

    generate_feed()

    try:
        server = RSSServerManager()
        server.port = 8080
        server.execute(DATA_DIR)
    except KeyboardInterrupt:
        _LOGGER.info("stopping the server")

    return 0


if __name__ == "__main__":
    main()
