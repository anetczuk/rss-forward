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

from rssforward.utils import stringisoauto_to_date, escape_html, normalize_string
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen
from rssforward.site.utils.react import extract_data_dict, get_nested_dict
from rssforward.site.utils.htmlbuild import convert_line, convert_list, convert_title, convert_content


_LOGGER = logging.getLogger(__name__)


MAIN_NAME = "pracuj.pl"
MAIN_URL = "https://www.pracuj.pl/"


@unique
class ParamsField(Enum):
    FILTER = "filter"
    LABEL = "label"
    URL = "url"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


#
class PracujPlGenerator(RSSGenerator):
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

    soup = BeautifulSoup(response.text, "html.parser")

    offers_content_list = soup.select('a[data-test*="link-offer"]')
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


def add_offer(feed_gen, label, offer_url=None, content=None, html_out_path=None):
    # sleep_random(3)
    if offer_url is not None:
        _LOGGER.info(f"getting offer details: {offer_url}")
        headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
        response = requests.get(offer_url, headers=headers, timeout=10)

        if response.status_code not in (200, 204):
            _LOGGER.warning("unable to get job offer content")
            return

        content = response.text

    soup = BeautifulSoup(content, "html.parser")

    data_dict = extract_data_dict(soup)
    if data_dict is None:
        return
    data_dict = get_nested_dict(data_dict, ["props", "pageProps"])

    queries_list = get_nested_dict(data_dict, ["dehydratedState", "queries"])
    if not queries_list:
        _LOGGER.warning("unable to get job data from url: %s", offer_url)
        return
    query_data = queries_list[0]
    offer_data = get_nested_dict(query_data, ["state", "data"])
    attributes = offer_data["attributes"]

    offer_id = data_dict["offerId"]
    offer_title = attributes["jobTitle"]
    offer_company = attributes["displayEmployerName"]
    offer_published = offer_data["publicationDetails"]["lastPublishedUtc"]

    if offer_url is None:
        offer_url = offer_data["offerURLName"]
        offer_url = f"{MAIN_URL}praca/{offer_url}"

    employment = attributes["employment"]
    # full_remote = employment["entirelyRemoteWork"]
    work_schedule = convert_work_schedule(employment["workSchedules"])
    contract_types = convert_contract_data(employment["typesOfContracts"])
    work_mode = convert_work_mode(employment["workModes"])

    ########

    feed_item = feed_gen.add_entry()

    feed_item.id(offer_id)

    feed_item.title(f"{label}: {offer_company} - {offer_title}")
    feed_item.author({"name": MAIN_NAME, "email": MAIN_NAME})

    # fill description
    desc_sections = offer_data["sections"]

    offer_desc = ""
    offer_desc += f"""<div style="margin-left: 12px">{contract_types}{work_schedule}{work_mode}</div>\n"""

    for sec_item in desc_sections:
        sec_content = convert_to_section(sec_item)
        offer_desc += f"{sec_content}<br/>\n"

    item_desc = offer_desc
    item_desc = normalize_string(item_desc)
    # item_desc = convert_to_html(item_desc)

    data_string = pprint.pformat(offer_data)
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

    if html_out_path:
        with open(html_out_path, "w", encoding="utf-8") as html_file:
            html_file.write(item_desc)

    feed_item.content(item_desc)

    # fill publish date
    item_date = stringisoauto_to_date(offer_published)
    feed_item.pubDate(item_date)

    feed_item.link(href=offer_url, rel="alternate")
    # feed_item.link( href=offer_url, rel='via')        # does not work in thunderbird


def convert_work_schedule(work_schedule_list):
    content_list = []
    for item in work_schedule_list:
        content_list.append(item["name"])
    if not content_list:
        return ""
    output = convert_list("Wymiar godzin:", content_list)
    return f"""{output}<br/>\n"""


def convert_contract_data(contract_data_list):
    content_list = []
    for item in contract_data_list:
        item_content = item["name"]
        salary = item["salary"]
        if salary:
            item_content += f""" {salary["from"]} - {salary["to"]}"""
            item_content += f""" {salary["currency"]["code"]} {salary["timeUnit"]["shortForm"]["name"]}"""
            item_content += f""" {salary["salaryKind"]["name"]}"""
        content_list.append(item_content)
    if not content_list:
        return ""
    output = convert_list("Rodzaj umowy:", content_list)
    return f"""{output}<br/>\n"""


def convert_work_mode(work_mode_list):
    content_list = []
    for item in work_mode_list:
        content_list.append(item["name"])
    if not content_list:
        return ""
    output = convert_list("Tryb pracy:", content_list)
    return f"""{output}<br/>\n"""


def convert_to_section(section_data):
    title = section_data.get("title")
    if title is None:
        return ""

    sub_sec_list = []

    model = section_data.get("model")
    if model is not None:
        model_content = convert_model(model)
        if model_content:
            sub_sec_list.append(model_content)

    sub_sections = section_data.get("subSections")
    if sub_sections is not None:
        for subsect in sub_sections:
            sub_content = convert_to_section(subsect)
            if sub_content:
                sub_sec_list.append(sub_content)

    if not sub_sec_list:
        return ""

    section_content = "<br/>\n".join(sub_sec_list)

    ret_content = ""
    if title:
        ret_content += """<!-- convert_to_section --><div style="margin-left: 12px">"""
        ret_content += convert_title(title)
        ret_content += section_content
        ret_content += "</div>\n"
    else:
        ret_content += f"{section_content}\n"
    return ret_content


def convert_model(model_data):
    title = None
    model_type = model_data["modelType"]

    if model_type == "open-dictionary":
        # section_name = model_data["dictionaryName"]
        items_list = []
        section_data = model_data["customItems"]
        items_list.extend([item_dict["name"] for item_dict in section_data])
        section_data = model_data["items"]
        items_list.extend([item_dict["name"] for item_dict in section_data])
        return convert_line(title, items_list, inline=True)

    if model_type == "open-dictionary-with-icons":
        # section_name = model_data["dictionaryName"]
        items_list = []
        section_data = model_data["customItems"]
        items_list.extend([item_dict["name"] for item_dict in section_data])
        section_data = model_data["items"]
        items_list.extend([item_dict["name"] for item_dict in section_data])
        return convert_list(title, items_list)

    if model_type == "bullets":
        section_data = model_data["bullets"]
        return convert_list(title, section_data)

    if model_type == "percentages":
        section_data = model_data["parts"]
        items_list = [f"""{item_dict["percent"]}% {item_dict["text"]}""" for item_dict in section_data]
        return convert_list(title, items_list)

    if model_type == "multi-paragraph":
        section_data = model_data["paragraphs"]
        return convert_content(title, section_data)

    if model_type == "gallery":
        # ignore
        return ""

    return f"<div>unhandled model type: {model_type}<br/>{model_data}</div>\n"


def sleep_random(max_seconds):
    rand_secs = random.randint(1, max_seconds)  # nosec
    time.sleep(rand_secs)


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return PracujPlGenerator(gen_params)
