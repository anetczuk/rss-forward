#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

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
from rssforward.access.keepassxcauth import KeepassxcAuth
from rssforward.source.earlystage import MAIN_URL


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure()

    auth = KeepassxcAuth(client_id="xxx", state_file_path="/tmp/xxx.assoc")  # nosec
    auth.connect()

    auth_data = auth.get_auth_data(MAIN_URL)
    _LOGGER.info("unlocking done, login: %s", auth_data.get("login"))


if __name__ == "__main__":
    main()
