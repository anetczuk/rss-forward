#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
import datetime
from enum import Enum, unique

from rssforward.utils import convert_to_html
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen
from rssforward.site.utils.ytdlpparser import parse_playlist


_LOGGER = logging.getLogger(__name__)


@unique
class ParamsField(Enum):
    URL = "url"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


class YouTubeGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()
        self.url = self.params.get(ParamsField.URL.value)
        self.items_per_fetch = self.params.get(ParamsField.ITEMSPERFETCH.value, 30)
        self.out_file = self.params.get(ParamsField.OUTFILE.value)

    def authenticate(self, login, password):
        # nothing to authenticate
        return True

    def generate(self) -> dict[str, str]:
        _LOGGER.info("========== running YouTube scraper ==========")

        if not self.url:
            _LOGGER.warning("unable to generate content, because no URL")
            return None

        # TODO: get items by recent date
        # 'upload_date'
        # recent_datetime = read_recent_date()
        # _LOGGER.info("getting librus data, recent date: %s", recent_datetime)

        data = parse_playlist(self.url, max_fetch=self.items_per_fetch)
        return self._generateFeed(data)

    def _generateFeed(self, yt_data):
        feed_gen = init_feed_gen(self.url, lang="en")
        feed_gen.title(yt_data["feed"]["title"])
        feed_gen.description(" ")  # required non-emptyfield
        channel_name = yt_data["feed"]["name"]

        entry_list = yt_data.get("entries", [])
        for item in entry_list:
            # pprint.pprint(item)
            add_entry(feed_gen, item, channel_name)

        out_file = self.out_file
        if not out_file:
            channel_id = yt_data["feed"]["id"]
            out_file = f"{channel_id}.xml"

        content = dumps_feed_gen(feed_gen)
        return {out_file: content}


# ============================================


def add_entry(feed_gen, data_dict, channel_name):
    feed_item = feed_gen.add_entry()
    item_title = data_dict["title"]
    item_url = data_dict["link"]

    feed_item.id(data_dict["id"])
    feed_item.author({"name": channel_name, "email": channel_name})
    feed_item.title(item_title)
    feed_item.link(href=item_url, rel="alternate")

    # fill description
    item_content = f"""{item_title}\n\n{item_url}"""
    item_content = convert_to_html(item_content)
    feed_item.content(item_content)

    # fill publish date
    item_date = datetime.datetime.fromisoformat(data_dict["published"])

    feed_item.pubDate(item_date)


# ============================================================


def get_generator(generator_params_dict) -> RSSGenerator:
    return YouTubeGenerator(generator_params_dict)
