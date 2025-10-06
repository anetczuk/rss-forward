#!/usr/bin/python3
#
# MIT License
#
# Copyright (c) 2025 Arkadiusz Netczuk <dev.arnet@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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

from rssforward import logger
from rssforward.source.nofluffjobs import get_offers_content
from rssforward.utils import write_data


_LOGGER = logging.getLogger(__name__)


def main():
    logger.configure_console()

    url = "https://nofluffjobs.com/pl/warszawa/C%2B%2B?sort=newest"

    # params = {
    #     ParamsField.FILTER.value: [
    #         {   ParamsField.LABEL.value: "Offers C++ Warsaw",
    #             ParamsField.URL.value: url,
    #             ParamsField.ITEMSPERFETCH.value: 2
    #         }
    #     ]
    # }
    # generator: RSSGenerator = get_generator(params)
    # gen_data = generator.generate()
    # print( gen_data.keys())

    # ruff: noqa: S108
    offers_content = get_offers_content("xxx", url, 1, "/tmp/nofluffjobs.html")
    if not offers_content:
        _LOGGER.error("FAILED")
        sys.exit(1)

    # ruff: noqa: S108
    out_path = "/tmp/nofluffjobs.xml"
    _LOGGER.info("writing rss to file: file://%s", out_path)
    write_data(out_path, offers_content)


if __name__ == "__main__":
    main()
