#!/usr/bin/env python3
#
# MIT License
#
# Copyright (c) 2021 Arkadiusz Netczuk <dev.arnet@gmail.com>
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
import argparse

# import pprint

from rssforward import logger
from rssforward.source.librus import generate_content, LibusGenerator
from rssforward.utils import write_data


_LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Test runner")
    parser.add_argument(
        "-u",
        "--user",
        action="store",
        required=True,
        default=None,
        help="User",
    )
    parser.add_argument(
        "-p",
        "--password",
        action="store",
        required=True,
        default=None,
        help="Password",
    )

    args = parser.parse_args()

    logger.configure_console()

    librus = LibusGenerator()
    librus.authenticate(args.user, args.password)

    librus_content = librus.generate()
    
    print( "xxxxx", librus_content )

    # if len(offers_list) != 1:
    #     _LOGGER.error("FAILED")
    #     sys.exit(1)
    #
    # full_url = offers_list[0]
    # offer_data = extract_offer_data(full_url)
    # # _LOGGER.info("offer_data:\n%s", pprint.pformat(offer_data))
    #
    # desc = offer_data["content"]
    #
    # content_path = "/tmp/pracujpl.html"
    # write_data(content_path, desc)
    # _LOGGER.info("content written to: %s", content_path)


if __name__ == "__main__":
    main()
