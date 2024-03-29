#!/usr/bin/python3
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

import sys
import json
import pprint

from rssforward import logger
from rssforward.site.utils.ytdlpparser import parse_playlist


def get_json(obj):
    return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))


def main():
    logger.configure()

    # ## playlist - gwiazdowski
    # url = "https://www.youtube.com/playlist?list=PLC9xjKm8G0LpgFgi-eF4YgvtMuogd1dHw"
    # info_dict = fetch_info(url, items_num=999999)
    # info_dict["entries"] = "xxx"
    # pprint.pprint( info_dict )
    # return

    ## playlist - youtube latino
    url = "https://www.youtube.com/playlist?list=PL1ebpFrA3ctH0QN6bribofTNpG4z2loWy"
    known = ["https://www.youtube.com/watch?v=aAbfzUJLJJE", "https://www.youtube.com/watch?v=3Q1DIHK2AIw"]

    ret_dict = parse_playlist(url, known)
    print("extracted rss channel data:")
    pprint.pprint(ret_dict)

    # rss_content = generate_items_rss(channel_data, host="the_host",
    #                                  url_dir_path="url_dir", local_dir_path="local_dir",
    #                                  store=False, check_local=False)
    # print(rss_content)


# =============================================================


if __name__ == "__main__":
    main()
    sys.exit(0)
