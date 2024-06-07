#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

try:
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=W0611
    import __init__
except ImportError:
    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded
    pass


import os
import pprint
from rssforward import logger
from rssforward.site.bulldogjob import get_generator
from rssforward.utils import write_data


def main():
    logger.configure()

    login, password = (None, None)

    filters = [
        {
            "label": "Offers C++ Warsaw",
            "url": "https://bulldogjob.pl/companies/jobs/s/city,Warszawa/skills,C++/order,published,desc",  # pylint: disable=C0301
            "outfile": "c_warsaw.xml",
        }
    ]
    params = {"filter": filters}

    generator = get_generator(params)
    generator.authenticate(login, password)
    generator_data = generator.generate()
    pprint.pprint(generator_data)
    for rss_out, content in generator_data.items():
        out_dir = os.path.join("/tmp", "rss-forward", "bulldog")  # nosec
        feed_path = os.path.join(out_dir, rss_out)
        feed_dir = os.path.dirname(feed_path)
        os.makedirs(feed_dir, exist_ok=True)
        print(f"writing content to file: {feed_path}")
        write_data(feed_path, content)


if __name__ == "__main__":
    main()
