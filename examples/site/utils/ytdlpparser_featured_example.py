#!/usr/bin/python3
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

import sys
import logging
import json
import pprint

from rssforward import logger
from rssforward.site.utils.ytdlpparser import parse_playlist


_LOGGER = logging.getLogger(__name__)


def get_json(obj):
    return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))


def main():
    logger.configure()

    # przygody przedsiebiorcow
    url = "https://www.youtube.com/@PrzygodyPrzedsiebiorcow/featured"
    ret_dict = parse_playlist(url)
    _LOGGER.info("extracted rss channel data:\n%s", pprint.pformat(ret_dict))


# =============================================================


if __name__ == "__main__":
    main()
    sys.exit(0)
