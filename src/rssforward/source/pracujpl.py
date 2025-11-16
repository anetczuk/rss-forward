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
from enum import Enum, unique
import datetime
import pprint

import random
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

from rssforward.utils import stringisoauto_to_date, escape_html, normalize_string
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen, add_data_to_feed
from rssforward.source.utils.react import extract_data_dict, get_nested_dict
from rssforward.source.utils.htmlbuild import convert_line, convert_list, convert_title, convert_content
from rssforward.source.utils.selenium import selenium_get_content


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


class PracujPlGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()
        self.filters_list = self.params.get(ParamsField.FILTER.value)

    def authenticate(self, _login, _password):
        return True

    def generate(self) -> dict[str, str]:
        _LOGGER.info("========== running %s scraper ==========", MAIN_NAME)
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


def get_offers_content(label, filter_url, filter_items, *, throw=True):
    offers_links_list = get_offers_links(filter_url, filter_items, throw=throw)
    if not offers_links_list:
        return None

    feed_gen: FeedGenerator = init_feed_gen(MAIN_URL)
    feed_gen.title(label)
    feed_gen.description(label)

    for full_url in offers_links_list:
        add_offer(feed_gen, label, full_url)

    try:
        content = dumps_feed_gen(feed_gen)
    except ValueError:
        _LOGGER.error("unable to dump feed, content:\n%s", feed_gen)
        raise

    return content


def add_offer(feed_gen, label, full_url, html_out_path=None):
    offer_data = extract_offer_data(full_url, html_out_path=html_out_path)

    pub_date: datetime.datetime = offer_data["pub_date"]
    curr_time = datetime.datetime.now(tz=datetime.timezone.utc)
    time_diff = curr_time - pub_date
    diff_days = time_diff.total_seconds() / (60 * 60 * 24)
    if diff_days > 7:
        ## do not add older offers - on the site refreshed/renewed offers change its ID, so
        ## the offer will appear again in RSS with original publish date
        return

    offer_data["title"] = label + ": " + offer_data["title"]
    add_data_to_feed(feed_gen, offer_data)


def get_offers_links(filter_url, filter_items, *, throw=True):
    _LOGGER.info("accessing offers list: %s", filter_url)
    response_text: str = selenium_get_content(filter_url)
    if not response_text:
        if throw:
            message = f"unable to get content from url: {filter_url}"
            raise RuntimeError(message)
        return None
    soup = BeautifulSoup(response_text, "html.parser")

    offers_links_list = soup.select('a[data-test*="link-offer"]')
    items_num = min(filter_items, len(offers_links_list))
    offers_links_tags = offers_links_list[0:items_num]

    full_list = []
    for offer_item in offers_links_tags:
        offer_url = offer_item["href"]
        full_url = urljoin(filter_url, offer_url)
        full_list.append(full_url)
    return full_list


def extract_offer_data(offer_url=None, content: str = None, html_out_path=None):
    # sleep_random(3)

    if offer_url:
        _LOGGER.info("extracting offer data: %s", offer_url)
        content: str = selenium_get_content(offer_url)
        if not content:
            _LOGGER.warning("unable to get job offer content")
            return None
    soup = BeautifulSoup(content, "html.parser")

    data_dict = extract_data_dict(soup)
    if data_dict is None:
        return None
    data_dict = get_nested_dict(data_dict, ["props", "pageProps"])

    queries_list = get_nested_dict(data_dict, ["dehydratedState", "queries"])
    if not queries_list:
        _LOGGER.warning("unable to get job data from url: %s", offer_url)
        return None
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

    # fill publish date
    item_date = stringisoauto_to_date(offer_published)

    return {
        "id": offer_id,
        "title": f"{offer_company} - {offer_title}",
        "author": {"name": MAIN_NAME, "email": MAIN_NAME},
        "content": item_desc,
        "pub_date": item_date,
        "link": offer_url,
    }


def convert_work_schedule(work_schedule_list):
    content_list = [item["name"] for item in work_schedule_list]
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
    content_list = [item["name"] for item in work_mode_list]
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
    factor = 1000
    # ruff: noqa: S311
    rand_secs = random.randint(1, max_seconds * factor)  # nosec
    time.sleep(rand_secs / factor)


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return PracujPlGenerator(gen_params)
