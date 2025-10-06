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

from rssforward import logger
from rssforward.site.theprotocol import get_generator
from rssforward.utils import write_data


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure()

    login, password = (None, None)

    filters = [
        {
            "label": "Offers C++ Warsaw",
            # "url": "https://theprotocol.it/filtry/c++;t/warszawa;wp?sort=date",  # pylint: disable=C0301
            "url": "https://theprotocol.it/filtry/c++;t/zdalna;rw?sort=date",  # pylint: disable=C0301
            "itemsperfetch": 2,
            "outfile": "c_warsaw.xml",
        },
    ]
    params = {"filter": filters}

    generator = get_generator(params)
    generator.authenticate(login, password)
    generator_data = generator.generate()
    _LOGGER.info("generator_data:\n%s", pprint.pformat(generator_data))
    for rss_out, content in generator_data.items():
        out_dir = os.path.join("/tmp", "rss-forward", "theprotocol")  # nosec
        feed_path = os.path.join(out_dir, rss_out)
        feed_dir = os.path.dirname(feed_path)
        os.makedirs(feed_dir, exist_ok=True)
        _LOGGER.info(f"writing content to file: {feed_path}")
        write_data(feed_path, content)


if __name__ == "__main__":
    main()
