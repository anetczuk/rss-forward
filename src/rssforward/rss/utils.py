#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from typing import Dict, Any

from feedgen.feed import FeedGenerator


_LOGGER = logging.getLogger(__name__)


def init_feed_gen(main_link, lang="pl") -> FeedGenerator:
    feed_gen = FeedGenerator()
    feed_gen.link(href=main_link)
    feed_gen.language(lang)
    return feed_gen


def add_data_to_feed(feed_gen: FeedGenerator, data_dict: Dict[str, Any]):
    feed_item = feed_gen.add_entry()

    feed_item.id(data_dict["id"])
    feed_item.title(data_dict["title"])
    feed_item.author(data_dict["author"])
    feed_item.content(data_dict["content"])
    feed_item.pubDate(data_dict["pub_date"])
    feed_item.link(href=data_dict["link"], rel="alternate")
    # feed_item.link( data_dict["link"], rel="via" )          # does not work in thunderbird


def dumps_feed_gen(feed_gen: FeedGenerator):
    items_num = len(feed_gen._FeedGenerator__feed_entries)  # pylint: disable=W0212
    _LOGGER.info("generating %s feed items", items_num)
    content_bytes = feed_gen.rss_str(pretty=True)
    return content_bytes.decode()
