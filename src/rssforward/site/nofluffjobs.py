#
# Copyright (c) 2025, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
from enum import Enum, unique
import datetime

import json
import requests

from bs4 import BeautifulSoup

from feedgen.feed import FeedGenerator

from rssforward.utils import (
    timestamp_to_date,
    write_data,
)
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen, add_data_to_feed


_LOGGER = logging.getLogger(__name__)


MAIN_NAME = "NoFluffJobs"
MAIN_URL = "https://nofluffjobs.com/"


@unique
class ParamsField(Enum):
    FILTER = "filter"
    LABEL = "label"
    URL = "url"
    ITEMSPERFETCH = "itemsperfetch"
    OUTFILE = "outfile"


class NoFluffJobsGenerator(RSSGenerator):
    def __init__(self, params_dict=None):
        super().__init__()
        self.params = {}
        if params_dict:
            self.params = params_dict.copy()
        self.filters_list = self.params.get(ParamsField.FILTER.value)

    def authenticate(self, login, password):
        return True

    def generate(self) -> dict[str, str]:
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


def get_offers_content(label, filter_url, filter_items, throw=True, html_out_path=None):
    offers_links_list = get_offers_links(filter_url, throw)
    if not offers_links_list:
        return None

    if filter_items:
        recent_items = min(filter_items, len(offers_links_list))
        offers_links_list = offers_links_list[-recent_items:]

    feed_gen: FeedGenerator = init_feed_gen(MAIN_URL)
    feed_gen.title(label)
    feed_gen.description(label)

    for full_url in offers_links_list:
        add_offer(feed_gen, label, full_url, html_out_path=html_out_path)

    try:
        content = dumps_feed_gen(feed_gen)
    except ValueError:
        _LOGGER.error(f"unable to dump feed, content:\n{feed_gen}")
        raise

    return content


def get_offers_links(filter_url, throw=True):
    # sleep_random(4)
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
    response = requests.get(filter_url, headers=headers, timeout=10)

    if response.status_code not in (200, 204):
        if throw:
            message = f"unable to get data: {response.status_code}"
            raise RuntimeError(message)
        return None

    content_bytes = response.content
    content = content_bytes.decode("utf-8")
    soup = BeautifulSoup(content, "html.parser")

    offer_json_list = soup.findAll("script", {"id": "serverApp-state"})
    if len(offer_json_list) < 1:
        _LOGGER.warning("unable to find job offer json")
        return None

    json_content = offer_json_list[0].string
    data_dict = json.loads(json_content)
    del data_dict["USER_COUNTRY"]
    del data_dict["__nghData__"]
    del data_dict["translations_pl-PL"]
    del data_dict["assigned on server"]
    for key in list(data_dict.keys()):
        if key.startswith("assets/"):
            del data_dict[key]
        if key.startswith("/joboffers/autocomplete"):
            del data_dict[key]
        if key.startswith("/joboffers/count"):
            del data_dict[key]
    # pprint.pprint(data_dict.keys())

    data_list = data_dict["STORE_KEY"]["searchResponse"]["postings"]

    offser_links = []
    for offer_data in data_list:
        data_posted = offer_data["posted"]  ## timestamp
        data_posted /= 1000  ## convert from millis to seconds
        post_date = timestamp_to_date(data_posted)
        data_id = f"""{offer_data["id"]}_{data_posted}"""

        data_url = offer_data["url"]
        offer_link = f"https://nofluffjobs.com/pl/job/{data_url}"

        result = {
            "id": data_id,
            "title": f"""{offer_data["name"]} - {offer_data["title"]}""",
            "author": {"name": MAIN_NAME, "email": MAIN_NAME},
            "pub_date": post_date,
            "link": offer_link,
        }
        offser_links.append(result)
    return offser_links


def add_offer(feed_gen, label, offer_data, html_out_path=None):
    offer_data = add_offer_content(offer_data, html_out_path=html_out_path)
    if not offer_data:
        return

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


def add_offer_content(offer_data, html_out_path=None):
    offer_url = offer_data["link"]

    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
    response = requests.get(offer_url, headers=headers, timeout=10)

    if response.status_code not in (200, 204):
        return None

    content_bytes = response.content
    content = content_bytes.decode("utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # offer_name_list = soup.findAll("div", {"class": "posting-details-description"})
    # if len(offer_name_list) < 1:
    #     _LOGGER.warning("unable to find job offer data")
    #     return None
    #
    # offer_name_div = offer_name_list[0]
    # offser_name_header_list = offer_name_div.findAll("h1")
    # if len(offser_name_header_list) < 1:
    #     _LOGGER.warning("unable to find job offer data")
    #     return None
    # offser_name = offser_name_header_list[0].text
    # offser_name = offser_name.strip()
    #
    # offer_company_list = offer_name_div.findAll("a")
    # if len(offer_company_list) < 1:
    #     _LOGGER.warning("unable to find job offer data")
    #     return None
    # offser_company = offer_company_list[0].text
    # offser_company = offser_company.strip()

    offer_req_tech = get_section(soup, "div", {"id": "posting-requirements"})
    if offer_req_tech is None:
        _LOGGER.warning("unable to find job offer data from %s", offer_url)
        return None
    offer_content_tag = offer_req_tech.parent
    content = str(offer_content_tag)

    salary_content = "unknown"
    offer_salaries = get_section(soup, "common-posting-salaries-list")
    if offer_salaries:
        salary_content = str(offer_salaries)

    content = f"""
<style>
common-image-blur {{
    display: none;
}}
ul li,
ul li div,
ul li aside {{
    display: inline;
}}

ul li img,
ul li svg,
ul li popover-content,
inline-icon {{
    display: none;
}}

.posting-info-row li a {{
    background-color: lightgray;
    margin-right: 12px;
}}

#posting-requirements ul li span {{
    background-color: lightgray;
    margin-right: 12px;
}}

#posting-seniority {{
    display: block;
}}

common-posting-time-info {{
    display: block;
}}

common-posting-translate-section {{
    display: none;
}}

common-posting-salaries-list .calculate {{
    display: none;
}}
</style>

<b style="font-size: 28px;">Wynagrodzenie:</b>
<br/>
{salary_content}
<br/>
{content}
<br/>
Id: {offer_data["id"]}
"""

    if html_out_path:
        write_data(html_out_path, content)

    offer_data["content"] = content
    return offer_data

    # offer_nice_tech = get_section(soup, "div", {"id": "posting-nice-to-have"})
    # if offer_req_tech is None:
    #     _LOGGER.warning("unable to find job offer data")
    #     return None
    #
    # offer_requirements = get_section(soup, "section", {"data-cy-section": "JobOffer_Requirements"})
    # if offer_req_tech is None:
    #     _LOGGER.warning("unable to find job offer data")
    #     return None
    #
    # offer_requirements = get_section(soup, "section", {"data-cy-section": "JobOffer_Requirements"})
    # if offer_req_tech is None:
    #     _LOGGER.warning("unable to find job offer data")
    #     return None


def get_section(soup, tag, selector_dict=None):
    offer_req_list = soup.findAll(tag, selector_dict)
    if len(offer_req_list) < 1:
        return None
    return offer_req_list[0]


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return NoFluffJobsGenerator(gen_params)
