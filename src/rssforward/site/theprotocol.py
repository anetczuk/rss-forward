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
import pprint

import random
from urllib.parse import urljoin
import requests

from bs4 import BeautifulSoup

from rssforward.utils import convert_to_html, stringisoauto_to_date, escape_html, normalize_string
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen
from rssforward.site.utils.react import extract_data_dict, get_nested_dict
from rssforward.site.utils.htmlbuild import convert_line, convert_list


_LOGGER = logging.getLogger(__name__)


MAIN_URL = "https://theprotocol.it/"


@unique
class ParamsField(Enum):
    FILTER = "filter"
    LABEL = "label"
    URL = "url"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


#
class TheProtocolGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()
        self.filters_list = self.params.get(ParamsField.FILTER.value)

    def authenticate(self, login, password):
        return True

    def generate(self) -> Dict[str, str]:
        _LOGGER.info("========== running theprotocol scraper ==========")
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

    offers_content_list = soup.select('a[href*="szczegoly/praca"]')
    items_num = min(filter_items, len(offers_content_list))
    offers_content_list = offers_content_list[0:items_num]

    for offer_item in offers_content_list:
        offer_url = offer_item["href"]
        full_url = urljoin(filter_url, offer_url)
        add_offer(feed_gen, label, full_url)

    try:
        content = dumps_feed_gen(feed_gen)
        return content
    except ValueError:
        _LOGGER.error(f"unable to dump feed, content:\n{feed_gen}")
        raise


def add_offer(feed_gen, label, offer_url=None, content=None):
    # sleep_random(3)
    if offer_url is not None:
        _LOGGER.info(f"getting offer details: {offer_url}")
        headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
        response = requests.get(offer_url, headers=headers, timeout=10)

        if response.status_code not in (200, 204):
            _LOGGER.warning("unable to get job offer content")
            return

        content = response.content
        content = content.decode("utf-8")

    soup = BeautifulSoup(content, "html.parser")

    data_dict = extract_data_dict(soup)
    if data_dict is None:
        return
    data_dict = get_nested_dict(data_dict, ["props", "pageProps", "offer"])

    attributes = data_dict["attributes"]

    offer_id = data_dict["id"]
    offer_title = attributes["title"]["value"]
    offer_company = attributes["employer"]["name"]
    offer_published = data_dict["publicationDetails"]["lastPublishedUtc"]
    offer_url = data_dict["offerUrl"]

    ########

    feed_item = feed_gen.add_entry()

    feed_item.id(offer_id)

    feed_item.title(f"{label}: {offer_company} - {offer_title}")
    feed_item.author({"name": "theprotocol.it", "email": "theprotocol.it"})

    # fill description
    desc_sections = data_dict["textSections"]

    offer_desc = ""
    for sec_item in desc_sections:
        sect_desc, found = convert_to_section(sec_item)
        offer_desc += sect_desc
        if found is False:
            _LOGGER.warning("unhandled section type: %s on address: %s", sec_item, offer_url)

    # data_string = pprint.pformat(data_dict)
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
</div>
"""
    feed_item.content(item_desc)

    # fill publish date
    item_date = stringisoauto_to_date(offer_published)
    feed_item.pubDate(item_date)

    feed_item.link(href=offer_url, rel="alternate")
    # feed_item.link( href=offer_url, rel='via')        # does not work in thunderbird


def convert_to_section(section_data):
    section_type = section_data.get("type")
    if section_type is None:
        return "", False

    elems = section_data.get("elements")
    if elems is None:
        return "", False

    if section_type == "technologies-expected":
        return convert_line("Wymagane:", elems), True

    if section_type == "technologies-optional":
        return convert_line("Mile widziane:", elems), True

    if section_type == "technologies-os":
        return convert_line("System operacyjny:", elems), True

    if section_type == "about-project":
        return convert_line("O projekcie:", elems, inline=False), True

    if section_type == "responsibilities":
        return convert_list("Zakres obowiązków:", elems), True

    if section_type == "requirements-expected":
        return convert_list("Wymagania:", elems), True

    if section_type == "requirements-optional":
        return convert_list("Mile widziane:", elems), True

    if section_type == "work-organization-work-style":
        return convert_list("Tak pracujemy:", elems), True

    if section_type == "training-space":
        return convert_list("Możliwości rozwoju:", elems), True

    if section_type == "offered":
        return convert_list("Oferujemy:", elems), True

    if section_type == "benefits":
        return convert_list("Benefity:", elems), True

    if section_type == "development-practices":
        return convert_list("Tak pracujemy nad projektem:", elems), True

    if section_type == "work-organization-team-members":
        return convert_list("Zespół:", elems), True

    if section_type == "work-organization-team-size":
        return convert_line("Wielkość zespołu:", elems), True

    if section_type == "recruitment-stages":
        return convert_line("Etapy rekrutacji:", elems), True

    if section_type == "about-us":
        return convert_line("O firmie:", elems, inline=False), True

    if section_type == "about-us-description":
        return convert_line("O firmie:", elems), True

    if section_type == "additional-module":
        return convert_line("Dodatkowe informacje:", elems), True

    if section_type == "work-time":
        return convert_list("Podział pracy:", elems), True

    if section_type == "about-us-gallery":
        return "", True

    if section_type == "about-hr-consulting-agency-client":
        return convert_line("O kliencie agencji:", elems, inline=False), True

    _LOGGER.warning("unhandled section type: %s", section_type)
    return f"<div>unhandled type: {section_type}<br/>{elems}</div>\n", False


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
    return TheProtocolGenerator(gen_params)
