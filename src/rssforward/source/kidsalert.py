#
# Copyright (c) 2025, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
import datetime
import random
import time

import pprint
import json
import requests

from feedgen.feed import FeedGenerator

from rssforward.utils import (
    write_data,
    normalize_string,
    escape_html,
)
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen, add_data_to_feed


_LOGGER = logging.getLogger(__name__)


MAIN_NAME = "KidsAlert"
MAIN_URL = "https://kidsalert.pl"


class KidsAlertGenerator(RSSGenerator):

    def authenticate(self, _login, _password):
        return True

    def generate(self) -> dict[str, str]:
        _LOGGER.info("========== running %s scraper ==========", MAIN_NAME)
        content = get_content()
        return {"news.xml": content}


def get_content(items_num=20, html_output=None):
    items_list = get_news_links(items_num, throw=False)
    if not items_list:
        return None

    feed_gen: FeedGenerator = init_feed_gen(MAIN_URL)
    feed_gen.title(MAIN_NAME)
    feed_gen.description(MAIN_NAME)

    for item_url in items_list:
        add_news(feed_gen, item_url, html_output)

    try:
        content = dumps_feed_gen(feed_gen)
    except ValueError:
        _LOGGER.error("unable to dump feed, content:\n%s", feed_gen)
        raise

    return content


def get_news_links(posts_num=9999, *, throw=True):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
    response = requests.get("https://kidsalert.pl/alerts/?lang=pl", headers=headers, timeout=10)

    if response.status_code not in (200, 204):
        if throw:
            message = f"unable to get data: {response.status_code}"
            raise RuntimeError(message)
        return None

    content_bytes = response.content
    content = content_bytes.decode("utf-8")

    data_list = json.loads(content)

    items_num = min(posts_num, len(data_list))
    data_list = data_list[0:items_num]
    return [f"""https://kidsalert.pl/alerts/{item["id"]}/?lang=pl""" for item in data_list]


def add_news(feed_gen, item_url, html_output=None):
    offer_data = extract_news_data(item_url)
    if not offer_data:
        return
    if html_output:
        _LOGGER.info("writing html content to file: %s", html_output)
        content = offer_data["content"]
        write_data(html_output, content)
    add_data_to_feed(feed_gen, offer_data)


def extract_news_data(item_url=None, content=None):
    # sleep_random(3)
    if item_url is not None:
        _LOGGER.info("getting offer details: %s", item_url)
        headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"}
        response = requests.get(item_url, headers=headers, timeout=10)

        if response.status_code not in (200, 204):
            _LOGGER.warning("unable to get job offer content")
            return None

        content = response.content
        content = content.decode("utf-8")

    data_dict = json.loads(content)

    id_string = str(data_dict["id"])
    version_string = str(data_dict["version"])
    id_value = f"{id_string}_{version_string}"

    title_text = data_dict["title"]

    created_text = data_dict["created"]
    utc_dt = datetime.datetime.fromisoformat(created_text)
    item_date = utc_dt.astimezone()

    content_text = data_dict["content"]
    item_desc = normalize_string(content_text)

    image_item = ""
    image_link = data_dict.get("image")
    if image_link:
        image_item = f"""<img src="{image_link}"></img>"""

    video_item = ""
    video_link = data_dict.get("video")
    if video_link:
        video_item = f"""Video: <a href="{video_link}">link</a>"""

    data_string = pprint.pformat(data_dict)
    data_string = escape_html(data_string)

    content = f"""\
{item_desc}

{video_item}

<br/>

{image_item}

<br/>
<br/>

<div>
ID: {id_value}<br/>
Data:<br/>
<pre>
{data_string}
</pre>
</div>
"""

    return {
        "id": id_value,
        "title": title_text,
        "author": {"name": MAIN_NAME, "email": MAIN_NAME},
        "content": content,
        "pub_date": item_date,
        "link": item_url,
    }


def sleep_random(max_seconds):
    # ruff: noqa: S311
    rand_secs = random.randint(1, max_seconds)  # nosec
    time.sleep(rand_secs)


# ============================================================


def get_generator(_gen_params=None) -> RSSGenerator:
    return KidsAlertGenerator()
