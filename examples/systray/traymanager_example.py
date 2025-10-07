#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import contextlib

with contextlib.suppress(ImportError):
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=E0401,W0611
    # ruff: noqa: F401
    import __init__

    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded


import logging

from rssforward import logger
from rssforward.systray.traymanager import TrayManager


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure()

    manager = TrayManager()
    manager.run_loop()

    _LOGGER.info("execution completed")


if __name__ == "__main__":
    main()
