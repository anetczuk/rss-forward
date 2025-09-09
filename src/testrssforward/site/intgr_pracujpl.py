#!/usr/bin/python3
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
import pprint

try:
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=W0611
    import __init__
except ImportError:
    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded
    pass

import sys

from rssforward import logger
from rssforward.site.pracujpl import (
    get_offers_links,
    extract_offer_data,
)


def main():
    logger.configure_console()

    url = "https://it.pracuj.pl/praca/warszawa;wp?sc=0&itth=41"

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

    offers_list = get_offers_links(url, 1)
    if len(offers_list) != 1:
        print("FAILED")
        sys.exit(1)

    full_url = offers_list[0]
    offer_data = extract_offer_data(full_url)
    pprint.pprint(offer_data)


if __name__ == "__main__":
    main()
