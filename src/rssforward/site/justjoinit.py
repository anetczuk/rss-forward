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
import time

import pprint
import json
import requests

from bs4 import BeautifulSoup

from rssforward.utils import convert_to_html, stringisoz_to_date, escape_html, normalize_string
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


def get_offers_content(label, filter_url, filter_items, throw=True, attempts=3):
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
        add_offer(feed_gen, label, offer, attempts=attempts)

    content = dumps_feed_gen(feed_gen)
    return content


def add_offer(feed_gen, label, data_dict, attempts=3):
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

    for rep in range(0, attempts):
        offer_desc = get_description(desc_url)
        if offer_desc is not None:
            break
        time.sleep(1.5)
        _LOGGER.error("no description for url (attempt: %s) %s", rep + 1, desc_url)
    else:
        _LOGGER.error("no description for url after %s attempts: %s", attempts, desc_url)
        offer_desc = ""

    item_desc = offer_desc
    item_desc = normalize_string(item_desc)
    item_desc = convert_to_html(item_desc)

    employment_details = ""
    employment_types = data_dict["employmentTypes"]
    for item in employment_types:
        emp_currency = item["currency"]
        emp_from = item["from"]
        emp_to = item["to"]
        emp_type = item["type"]
        emp_gross = item["gross"]
        emp_currency = emp_currency.upper()
        gross_label = ""
        if emp_gross:
            gross_label = "Gross"
        else:
            gross_label = "Net"
        employment_details += (
            f"<div><b>Wynagrodzenie:</b> {emp_from} - {emp_to} {emp_currency} {gross_label} {emp_type}</div>\n"
        )

    data_string = pprint.pformat(data_dict)
    data_string = escape_html(data_string)

    item_desc = f"""\
{employment_details}

<br/>

{item_desc}

<br/>

<div>
ID: {item_id}<br/>
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

    for _ in range(0, 2):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code in (200, 204):
                # got response - break the loop
                break
            # sometimes server responds witn code 500 - in this case send another request
            _LOGGER.warning(f"unable to get description from url: {url} response: {response.status_code}")
        except requests.exceptions.ReadTimeout as exc:
            _LOGGER.warning(f"unable to get description from url: {url} exception: {exc}")
        # next iteration
        time.sleep(2.0)
    else:
        # could not reach description page
        _LOGGER.warning(f"unable to get description from url: {url} after several attempts")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    ## remove all style elements
    for style in soup.find_all("style"):
        style.decompose()

    # data_dict = extract_data_dict(soup)
    # if data_dict is None:
    #     _LOGGER.warning(f"unable to extract data from response: {url}\nsoup object: %s", soup)
    #     return None
    # data_dict = get_nested_dict(data_dict, ["props", "pageProps", "offer"])
    # # pprint.pprint(data_dict)
    # data_body = data_dict.get("body")
    # return data_body

    content_list = []

    tech_stack_list = soup.find_all("h2", attrs={"class": "MuiTypography-root"})
    for title_item in tech_stack_list:
        title_content = str(title_item)
        if "Tech stack" not in title_content:
            continue
        tech_div = title_item.parent
        ## remove all ul elements
        for ul_elem in tech_div.find_all("li"):
            ul_elem.decompose()
        content_list.append(str(tech_div))
        break

    job_desc_list = soup.find_all("h3", attrs={"class": "MuiTypography-root"})
    for title_item in job_desc_list:
        title_content = str(title_item)
        if "Job description" not in title_content:
            continue

        title_parent = title_item.parent
        desc_div = title_parent.nextSibling
        desc_parent = desc_div.parent
        content_list.append(str(desc_parent))
        break

    if len(content_list) == 2:
        content_list.insert(1, "")

    ret_content = "\n".join(content_list)
    return ret_content


# ============================================================


def get_generator(gen_params=None) -> RSSGenerator:
    return JustJoinItGenerator(gen_params)
