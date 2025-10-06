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

import os
import logging
import pprint

from rssforward import logger, PKG_DIR
from rssforward.configfile import load_config


_LOGGER = logging.getLogger(__name__)

EXAMPLES_DIR = os.path.join(PKG_DIR, os.pardir, os.pardir, "examples")


def main():
    logger.configure()
    config_path = os.path.join(EXAMPLES_DIR, "config_example.toml")
    config_dir = load_config(config_path)
    _LOGGER.info("config_dir:\n%s", pprint.pformat(config_dir))


if __name__ == "__main__":
    main()
