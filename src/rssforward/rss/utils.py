#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging

from feedgen.feed import FeedGenerator


_LOGGER = logging.getLogger(__name__)


def init_feed_gen(main_link, lang="pl") -> FeedGenerator:
    feed_gen = FeedGenerator()
    feed_gen.link(href=main_link)
    feed_gen.language(lang)
    return feed_gen


def dumps_feed_gen(feed_gen: FeedGenerator):
    items_num = len(feed_gen._FeedGenerator__feed_entries)  # pylint: disable=W0212
    _LOGGER.info("generating %s feed items", items_num)
    content_bytes = feed_gen.rss_str(pretty=True)
    return content_bytes.decode()
