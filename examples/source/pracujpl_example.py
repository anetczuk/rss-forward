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

from rssforward import logger
from rssforward.source.pracujpl import get_generator, add_offer
from rssforward.utils import write_data
from rssforward.rss.utils import init_feed_gen


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure()

    login, password = (None, None)

    filters = [
        {
            "label": "Offers C++ Warsaw",
            "url": "https://it.pracuj.pl/praca/warszawa;wp?sc=0&itth=41",  # pylint: disable=C0301
            "itemsperfetch": 1,
            "outfile": "c_warsaw.xml",
        },
    ]
    params = {"filter": filters}

    generator = get_generator(params)
    generator.authenticate(login, password)
    generator_data = generator.generate()
    # pprint.pprint(generator_data)
    for rss_out, content in generator_data.items():
        out_dir = os.path.join("/tmp", "rss-forward", "pracujpl")  # nosec
        feed_path = os.path.join(out_dir, rss_out)
        feed_dir = os.path.dirname(feed_path)
        os.makedirs(feed_dir, exist_ok=True)
        _LOGGER.info("writing content to file: %s", feed_path)
        write_data(feed_path, content)

    # ======================================

    feed_gen = init_feed_gen("pracuj.pl")
    feed_gen.title("offer feed")
    feed_gen.description("nice offers")

    offer_url = "https://www.pracuj.pl/praca/embedded-application-developer-digital-experience-platform-warszawa,oferta,1003409341"  # pylint: disable=C0301
    out_path = os.path.join("/tmp", "rss-forward", "pracujpl", "offer.html")  # nosec
    html_dir = os.path.dirname(out_path)
    os.makedirs(html_dir, exist_ok=True)
    add_offer(feed_gen, "the offer", offer_url, html_out_path=out_path)


if __name__ == "__main__":
    main()
