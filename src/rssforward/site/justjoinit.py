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

import pprint
import json
import requests

from bs4 import BeautifulSoup

from rssforward.utils import convert_to_html, stringisoz_to_date
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen


_LOGGER = logging.getLogger(__name__)


MAIN_URL = "https://justjoin.it/"


@unique
class ParamsField(Enum):
    FILTER = "filter"
    LABEL = "label"
    URL = "url"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


#
class JustJoinItGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()

        self.filters_list = self.params.get(ParamsField.FILTER.value)

    def authenticate(self, login, password):
        return True

    def generate(self) -> Dict[str, str]:
        _LOGGER.info("========== running justjoinit scraper ==========")
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
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
        "Version": "2",
    }
    response = requests.get(filter_url, headers=headers, timeout=30)

    if response.status_code not in (200, 204):
        if throw:
            raise RuntimeError(f"unable to get data: {response.status_code}")
        return None

    response_json = json.loads(response.text)

    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title(label)
    feed_gen.description(label)

    json_offers_list = response_json["data"]
    items_num = min(filter_items, len(json_offers_list))
    json_offers_list = json_offers_list[0:items_num]

    _LOGGER.info("found %s items", len(json_offers_list))
    for offer in json_offers_list:
        add_offer(feed_gen, label, offer)

    content = dumps_feed_gen(feed_gen)
    return content


def add_offer(feed_gen, label, data_dict):
    offer_title = data_dict["title"]
    offer_company = data_dict["companyName"]
    offer_published = data_dict["publishedAt"]
    # print(f"  {offer_company} {offer_title} {offer_published}")

    ########

    requiredSkills = data_dict.get("requiredSkills")
    if isinstance(requiredSkills, list):
        data_dict["requiredSkills"] = sorted(requiredSkills)

    feed_item = feed_gen.add_entry()

    slug = data_dict["slug"]

    # data_hash = calculate_dict_hash(data_dict)
    # calculating hash from data dict is to "fragile"
    # add date to prevent hash collision (very unlikely, but still...)
    item_id = f"{offer_published}_{slug}"
    feed_item.id(item_id)

    feed_item.title(f"{label}: {offer_company} - {offer_title}")
    feed_item.author({"name": "justjoin.it", "email": "justjoin.it"})

    # fill description
    desc_url = f"https://justjoin.it/offers/{slug}"
    offer_desc = get_description(desc_url)
    item_desc = convert_to_html(offer_desc)
    data_string = pprint.pformat(data_dict)
    item_desc = f"""\
{item_desc}

<br/>

<div>
Data:<br/>
<pre>
{data_string}
</pre>
</div>
"""
    feed_item.content(item_desc)

    # fill publish date
    item_date = stringisoz_to_date(offer_published)
    feed_item.pubDate(item_date)
    feed_item.link(href=desc_url, rel="alternate")
    # feed_item.link( href=desc_url, rel='via')        # does not work in thunderbird


def get_description(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
        "Version": "2",
    }
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code not in (200, 204):
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    found = soup.find_all("div", attrs={"class": "MuiBox-root css-qal8sw"})
    if len(found) > 1:
        return str(found[1])
    return None


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return JustJoinItGenerator(gen_params)
