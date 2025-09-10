#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
import time
from typing import Dict
from enum import Enum, unique

import random
import pprint
import json
import requests

from bs4 import BeautifulSoup

from rssforward.utils import convert_to_html, string_to_date, escape_html, normalize_string
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen


_LOGGER = logging.getLogger(__name__)


MAIN_URL = "https://bulldogjob.pl/"


@unique
class ParamsField(Enum):
    FILTER = "filter"
    LABEL = "label"
    URL = "url"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


#
class BullDogJobGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()
        self.filters_list = self.params.get(ParamsField.FILTER.value)

    def authenticate(self, login, password):
        return True

    def generate(self) -> Dict[str, str]:
        _LOGGER.info("========== running bulldogjob scraper ==========")
        if self.filters_list is None:
            _LOGGER.info("nothing to get - no filters")
            return {}

        ret_dict = {}
        for filter_data in self.filters_list:
            filter_label = filter_data.get(ParamsField.LABEL.value)
            filter_url = filter_data.get(ParamsField.URL.value)
            filter_items = filter_data.get(ParamsField.ITEMSPERFETCH.value, 20)
            _LOGGER.info("accessing: %s", filter_label)
            outfile = filter_data.get(ParamsField.OUTFILE.value)
            content = get_offers_content(filter_label, filter_url, filter_items)
            ret_dict[outfile] = content
        return ret_dict


def get_offers_content(label, filter_url, filter_items, throw=True):
    # sleep_random(4)
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
    response = requests.get(filter_url, headers=headers, timeout=10)

    if response.status_code not in (200, 204):
        if throw:
            raise RuntimeError(f"unable to get data: {response.status_code}")
        return None

    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title(label)
    feed_gen.description(label)

    content = response.content
    content = content.decode("utf-8")
    soup = BeautifulSoup(content, "html.parser")

    offers_content_list = soup.select(".container a")
    items_num = min(filter_items, len(offers_content_list))
    offers_content_list = offers_content_list[0:items_num]

    for offer_item in offers_content_list:
        offer_url = offer_item["href"]
        add_offer(feed_gen, label, offer_url)

    content = dumps_feed_gen(feed_gen)
    return content


def add_offer(feed_gen, label, offer_url):
    # sleep_random(4)
    _LOGGER.info(f"getting offer details: {offer_url}")
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
    response = requests.get(offer_url, headers=headers, timeout=10)

    if response.status_code not in (200, 204):
        _LOGGER.warning(f"unable to get job offer content, response status: {response.status_code}")
        return

    content = response.content
    content = content.decode("utf-8")
    soup = BeautifulSoup(content, "html.parser")

    offer_json_list = soup.findAll("script", {"type": "application/ld+json"})
    if len(offer_json_list) < 1:
        _LOGGER.warning("unable to find job offer json")
        return

    json_content = offer_json_list[0].string
    data_dict = json.loads(json_content)

    offer_id = data_dict["@id"]
    offer_title = data_dict["title"]
    offer_company = data_dict["hiringOrganization"]["name"]
    offer_published = data_dict["datePosted"]

    ########

    feed_item = feed_gen.add_entry()

    feed_item.id(offer_id)

    feed_item.title(f"{label}: {offer_company} - {offer_title}")
    feed_item.author({"name": "bulldogjob.pl", "email": "bulldogjob.pl"})

    # fill description
    offer_desc = data_dict["description"]

    item_desc = offer_desc
    item_desc = normalize_string(item_desc)
    item_desc = convert_to_html(item_desc)

    data_string = pprint.pformat(data_dict)
    data_string = escape_html(data_string)

    item_desc = f"""\
{item_desc}

<br/>

<div>
ID: {offer_id}<br/>
Data:<br/>
<pre>
{data_string}
</pre>
</div>"""
    feed_item.content(item_desc)

    # fill publish date
    item_date = string_to_date(offer_published)
    feed_item.pubDate(item_date)

    feed_item.link(href=offer_url, rel="alternate")
    # feed_item.link( href=offer_url, rel='via')        # does not work in thunderbird


def match_nested(item_list, nested_list):
    if not nested_list:
        return item_list
    sub_list = []
    tag = nested_list[0]
    for item in item_list:
        found = item.find(tag)
        if found:
            sub_list.append(found)
    return match_nested(sub_list, nested_list[1:])


def sleep_random(max_seconds):
    rand_secs = random.randint(1, max_seconds)  # nosec
    time.sleep(rand_secs)


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return BullDogJobGenerator(gen_params)
