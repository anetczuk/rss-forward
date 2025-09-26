#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
from typing import Dict
from enum import Enum, unique

from feedgen.feed import FeedGenerator

from rssforward.utils import escape_html, normalize_string, prepare_filename
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen, add_data_to_feed
from rssforward.access.facebookscraper import FacebookScraper


_LOGGER = logging.getLogger(__name__)


MAIN_NAME = "facebook pages"
MAIN_URL = "https://www.facebook.com"


@unique
class ParamsField(Enum):
    FILTER = "filter"
    LABEL = "label"
    PAGE = "page"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


#
class FacebookPagesGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()
        self.filters_list = self.params.get(ParamsField.FILTER.value)

    def authenticate(self, login, password):
        return True

    def generate(self) -> Dict[str, str]:
        _LOGGER.info(f"========== running {MAIN_NAME} scraper ==========")
        if self.filters_list is None:
            _LOGGER.info("nothing to get - no filters")
            return {}

        ret_dict = {}
        for filter_data in self.filters_list:
            filter_page = filter_data.get(ParamsField.PAGE.value)
            filter_label = filter_data.get(ParamsField.LABEL.value)
            filter_items = filter_data.get(ParamsField.ITEMSPERFETCH.value, 20)
            _LOGGER.info("accessing: %s '%s'", filter_page, filter_label)
            outfile = filter_data.get(ParamsField.OUTFILE.value)
            if not outfile:
                outfile = prepare_filename(filter_label) + ".xml"
            content = get_page_content(filter_label, filter_page, filter_items)
            ret_dict[outfile] = content
        return ret_dict


def get_page_content(label, page_id, posts_num):
    with FacebookScraper() as scraper:
        items_list = scraper.get_page_items(page_id, posts_num)
        _LOGGER.debug("found items: %s", len(items_list))

        feed_gen: FeedGenerator = init_feed_gen(MAIN_URL)
        feed_gen.title(label)
        feed_gen.description(label)

        page_title = scraper.title

        for item_dict in items_list:
            rss_data = convert_item_data(page_title, item_dict)
            add_data_to_feed(feed_gen, rss_data)

        try:
            content = dumps_feed_gen(feed_gen)
            return content
        except ValueError:
            _LOGGER.error(f"unable to dump feed, content:\n{feed_gen}")
            raise


def get_posts_links(scraper: FacebookScraper, page_id, posts_num):
    posts_list = scraper.get_page_posts(page_id)
    items_num = min(posts_num, len(posts_list))
    posts_list = posts_list[0:items_num]
    return [(item[2], item[3]) for item in posts_list]


def convert_item_data(page_title, post_details, html_out_path=None):
    item_id = post_details["id"]
    # fill description
    item_desc = post_details["content"]
    item_desc = item_desc.replace("\n", "</br>")
    item_desc = f"""<div style="margin-left: 12px">{item_desc}</div>\n"""
    item_desc = normalize_string(item_desc)
    # item_desc = convert_to_html(item_desc)

    date_content = ""
    event_date = post_details["event_date"]
    if event_date:
        date_string = escape_html(event_date)
        date_content = """\
<b>Date</b>: {date_string}
<br/>
<br/>"""

    item_desc = f"""\
{date_content}
<b>Description</b>:
<br/>
{item_desc}
<br/>
<br/>
Id: {item_id}
"""

    if html_out_path:
        with open(html_out_path, "w", encoding="utf-8") as html_file:
            html_file.write(item_desc)

    title = post_details["title"]
    if title:
        if event_date:
            date_string = escape_html(event_date)
            title = f"{title} - {date_string}"
    else:
        title = "Post"

    return {
        "id": item_id,
        "title": title,
        "author": {"name": page_title, "email": page_title},
        "content": item_desc,
        "pub_date": post_details["pub_date"],
        "link": post_details["url"],
    }


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return FacebookPagesGenerator(gen_params)
