#
# Copyright (c) 2025, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
import time

import random
from urllib.parse import urljoin
import requests

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

from rssforward.utils import normalize_string, string2_to_date
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen, add_data_to_feed
from rssforward.source.utils.htmlbuild import convert_line, convert_list, convert_title, convert_content


_LOGGER = logging.getLogger(__name__)


MAIN_NAME = "UNTS Warszawa"
MAIN_URL = "http://unts.waw.pl/"


class UNTSGenerator(RSSGenerator):

    def authenticate(self, _login, _password):
        return True

    def generate(self) -> dict[str, str]:
        _LOGGER.info(f"========== running {MAIN_NAME} scraper ==========")
        content = get_content()
        return {"news.xml": content}


def get_content():
    news_links = get_news_links(10, throw=False)
    if not news_links:
        return None

    feed_gen: FeedGenerator = init_feed_gen(MAIN_URL)
    feed_gen.title(MAIN_NAME)
    feed_gen.description(MAIN_NAME)

    for full_url in news_links:
        add_news(feed_gen, full_url)

    try:
        content = dumps_feed_gen(feed_gen)
    except ValueError:
        _LOGGER.error(f"unable to dump feed, content:\n{feed_gen}")
        raise

    return content


def get_news_links(posts_num, throw=True):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
    response = requests.get(MAIN_URL, headers=headers, timeout=10)

    if response.status_code not in (200, 204):
        if throw:
            message = f"unable to get data: {response.status_code}"
            raise RuntimeError(message)
        return None

    content_bytes = response.content
    content = content_bytes.decode("utf-8")

    soup = BeautifulSoup(content, "html.parser")

    full_list = []
    sections_list = soup.find_all("div", attrs={"class": "appBoxOuter"})
    for section in sections_list:
        if "Aktualności" not in section.text:
            continue
        articles_list = section.find_all("div", attrs={"class": "article"})
        for article in articles_list:
            news_title = article.find_all("h3", attrs={"class": "title"})[0]
            link = news_title.select("a")[0]
            item_url = link["href"]
            full_url = urljoin(MAIN_URL, item_url)

            news_date = article.find_all("span", attrs={"class": "date"})[0]
            news_date = news_date.text
            space_index = news_date.index(" ")
            news_date = news_date[:space_index]
            full_list.append((full_url, news_date))
    items_num = min(posts_num, len(full_list))
    return full_list[0:items_num]


def add_news(feed_gen, full_url):
    offer_data = extract_news_data(full_url)
    add_data_to_feed(feed_gen, offer_data)


def extract_news_data(news_data=None, content: str = None):
    news_url = news_data[0]
    news_date = news_data[1]

    # sleep_random(3)
    if news_url is not None:
        _LOGGER.info(f"getting offer details: {news_url}")
        headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
        response = requests.get(news_url, headers=headers, timeout=10)

        if response.status_code not in (200, 204):
            _LOGGER.warning("unable to get job offer content")
            return None

        content_bytes = response.content
        content = content_bytes.decode("utf-8")

    soup = BeautifulSoup(content, "html.parser")

    id_pos = news_url.index("id=")
    id_value = news_url[id_pos + 3 :]

    content_list = soup.find_all("div", attrs={"class": "Fullcontent"})
    content_tag = content_list[0]

    titles_list = content_tag.find_all("h2", attrs={"class": "title"})
    title_item = titles_list[0]
    title_span = title_item.select_one("span")
    title_text = title_span.text

    item_desc = str(content_tag)
    item_desc = normalize_string(item_desc)
    # item_desc = convert_to_html(item_desc)

    item_date = string2_to_date(news_date)

    return {
        "id": id_value,
        "title": title_text,
        "author": {"name": MAIN_NAME, "email": MAIN_NAME},
        "content": item_desc,
        "pub_date": item_date,
        "link": news_url,
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
    # ruff: noqa: S311
    rand_secs = random.randint(1, max_seconds)  # nosec
    time.sleep(rand_secs)


# ============================================================


def get_generator(_gen_params=None) -> RSSGenerator:
    return UNTSGenerator()
