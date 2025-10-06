#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)
# pylint: disable=C0103 (invalid-name)

import logging
import time
import datetime
import locale

import threading
from contextlib import contextmanager

import selenium.common
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from rssforward.utils import read_data, write_data, add_timezone, calculate_str_hash


_LOGGER = logging.getLogger(__name__)


lib_logger = logging.getLogger("selenium.webdriver")
lib_logger.setLevel(logging.WARNING)

lib_logger = logging.getLogger("urllib3.connectionpool")
lib_logger.setLevel(logging.WARNING)


MAIN_URL = "https://www.facebook.com"


class FacebookScraper:
    HEADLESS = True

    def __init__(self, headless=None):
        self.headless = headless
        if self.headless is None:
            self.headless = FacebookScraper.HEADLESS
        self.driver = self._init_driver()
        self.title = None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        """Exit context manager."""
        self.close()

    def close(self):
        if self.headless:
            self.driver.quit()

    def get_title(self) -> str:
        return self.title

    ## returns: {"id": str, "title": str, "event_date": datetime, "place": str, "content": str,
    ##           "pub_date": datetime, "url": str }
    def get_page_items(self, page_id, items_number=None):
        _LOGGER.info("getting page data from: %s", page_id)
        items_list = self.get_page_posts(page_id)
        if items_number is not None:
            items_num = min(items_number, len(items_list))
            items_list = items_list[0:items_num]

        items_data = []
        for item in items_list:
            event_title = item[1]
            if event_title is None:
                ## post data: None, None, post_link, post_pub_date, post_content
                ## https://www.facebook.com/{page_id}/posts/{post_id}?params
                post_link = item[2]
                if post_link is None:
                    _LOGGER.error("skipping post - could not get required data")
                    continue
                post_date = item[3]
                post_content = item[4]
                ## extracting post_id from post url is not reliable - facebook changes the value more or less once a day
                ## so we need to calculate hash from content
                hash_input = f"{post_date}_{post_content}"
                post_id = calculate_str_hash(hash_input)
                # post_id = extract_post_id_from_url(post_link)
                # if post_id is None:
                #     _LOGGER.error("skipping post - could not get required data")
                #     continue
                post_details = {
                    "id": post_id,
                    "type": "post",
                    "title": item[0],
                    "event_date": None,
                    "place": None,
                    "content": post_content,
                    "pub_date": post_date,
                    "url": post_link,
                }
                items_data.append(post_details)

            else:
                ## event data: event_title, event_date, event_link, event_pub_date, None
                event_link = item[2]
                event_details = self.get_event_details(event_link)
                if event_details:
                    event_details["pub_date"] = item[3]
                    items_data.append(event_details)

        return items_data

    def get_page_posts(self, page_id):
        self.driver.get(f"{MAIN_URL}/{page_id}/?locale=en")

        self.title = self.driver.title

        self._accept_cookies()
        self._close_login_popup()
        self._hide_login_bar()

        time.sleep(2)  ## wait for article elements

        found_articles = []
        article_list = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet]")
        if not article_list:
            _LOGGER.error("could not get posts list")
            # curr_size = self.driver.get_window_size()
            # self.driver.set_window_size(curr_size["width"], curr_size["height"] * 2)
            self._take_screenshot(page_id)
            return []

        _LOGGER.debug("found article elements: %s", len(article_list))
        for article in article_list:
            tag_pagelet = article.get_attribute("data-pagelet")
            if not tag_pagelet.startswith("TimelineFeedUnit"):
                _LOGGER.debug("skipping article tag: %s", tag_pagelet)
                continue
            ## single post
            _LOGGER.debug("found article tag: %s", tag_pagelet)

            post_messages = article.find_elements(By.CSS_SELECTOR, "[data-ad-rendering-role='story_message']")
            if post_messages:
                ## regular post case
                post_item = post_messages[0]

                ## expand description
                see_more_expanded = self._expand_see_more(post_item)
                if see_more_expanded is False:
                    _LOGGER.warning("could not expand description")
                else:
                    _LOGGER.debug("'See more' expanded")

                post_href = None
                pub_date = None
                link_list = article.find_elements(By.CSS_SELECTOR, "a[role='link']")
                for item in link_list:
                    href = item.get_attribute("href")
                    if "posts" not in href:
                        continue
                    post_href = href
                    pub_date = pub_string_to_date(item.text)
                    break

                if not post_href:
                    _LOGGER.error("could not find post URL")
                    continue

                post_href = post_href.split("?")[0]
                post_content = post_item.text
                post_title = get_content_title(post_content, 40)
                post_title = f"{post_title}"

                ## post title
                ## post has no start date
                ## add: None, None, post_link, post_pub_date, post_content
                article_data = []
                article_data.append(post_title)
                article_data.append(None)
                article_data.append(post_href)  ## link
                article_data.append(pub_date)
                article_data.append(post_content)  ## content
                found_articles.append(article_data)
                continue

            ## event case
            link_list = article.find_elements(By.CSS_SELECTOR, "a[aria-label]")
            _LOGGER.debug("found article links: %s", len(link_list))
            pub_date = None
            for item in link_list:
                item_children = item.find_elements(By.XPATH, "*")
                if len(item_children) < 1:
                    pub_date = pub_string_to_date(item.text)
                    continue
                span_list = item.find_elements(By.TAG_NAME, "span")
                _LOGGER.debug("found link spans: %s", len(span_list))
                ## event case
                href = item.get_attribute("href")
                article_data = []
                for span in span_list:
                    children = span.find_elements(By.XPATH, "*")
                    if len(children) > 0:
                        continue
                    content = span.text
                    ## replace strange whitespaces (e.g. non-breaking space) with regular space
                    content = " ".join(content.split())
                    article_data.append(content)
                if article_data:
                    href = href.split("?")[0]
                    article_data.reverse()
                    article_data.append(href)
                    article_data.append(pub_date)
                    article_data.append(None)
                    ## event has no content on main page
                    ## add: event_title, event_date, event_link, event_pub_date, None
                    found_articles.append(article_data)
        return found_articles

    ## returns: {"id": str, "title": str, "date": datetime, "place": str, "content": str}
    def get_event_details(self, details_url):
        _LOGGER.info("scrapping post data from: %s", details_url)

        event_id = extract_event_id_from_url(details_url)
        if event_id is None:
            return None

        self.driver.get(details_url)

        self._accept_cookies()
        self._close_login_popup()
        self._hide_login_bar()

        time.sleep(1)  ## wait for 'See more' to be clickable

        ## main section
        main_section_list = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label='Event Permalink']")
        _LOGGER.debug("found main sections: %s", len(main_section_list))
        if len(main_section_list) != 1:
            _LOGGER.warning("unable to get main section, got: %s", len(main_section_list))
            return None

        main_data_dict = {}
        main_section = main_section_list[0]

        ## expand description
        see_more_expanded = self._expand_see_more(main_section)
        if see_more_expanded is False:
            _LOGGER.warning("could not expand description")
        else:
            _LOGGER.debug("'See more' expanded")

        ## extract data
        mainbutton_list = main_section.find_elements(By.CSS_SELECTOR, "[role='button']")
        for button in mainbutton_list:
            found_data = []
            span_list = button.find_elements(By.TAG_NAME, "span")
            # span_list = button.select('span')
            for span in span_list:
                children = span.find_elements(By.XPATH, "*")
                if len(children) > 0:
                    continue
                content = span.text
                content.strip()
                ## replace strange whitespaces (e.g. non-breaking space) with regular space
                content = " ".join(content.split())
                found_data.append(content)
            if found_data:
                main_data_dict["title"] = found_data[1]
                main_data_dict["place"] = found_data[2]
                main_data_dict["event_date"] = found_data[0]
                break
        if not main_data_dict:
            _LOGGER.warning("unable to get main data")
            return None

        # source_code = script.get_attribute("outerHTML")

        main_data_dict = {"id": event_id, "type": "event", "url": details_url} | main_data_dict

        ## find description
        span_list = main_section.find_elements(By.CSS_SELECTOR, "span")
        for span in span_list:
            try:
                description = span.text
                see_less_pos = description.index("See less")
                if see_less_pos >= 0:
                    description = description[:see_less_pos]
                description = description.strip()
                main_data_dict["content"] = description

            # ruff: noqa: PERF203
            except ValueError:
                pass

            else:
                _LOGGER.debug("found description")
                return main_data_dict

        _LOGGER.error("could not get post description")
        # curr_size = self.driver.get_window_size()
        # self.driver.set_window_size(curr_size["width"], curr_size["height"] * 2)
        self._take_screenshot(event_id)
        return None

    # def _find_leaf_elements(self, element, selector: By, value: str):
    #     ret_list = []
    #     found_list = element.find_elements(selector, value)
    #     while found_list:
    #         item = found_list.pop(0)
    #         item_elements = self._find_leaf_elements(item, selector, value)
    #         if not item_elements:
    #             ## no matching children - leaf element
    #             ret_list.append(item)
    #     return ret_list

    ## expand post description to see whole content
    def _expand_see_more(self, item) -> bool:
        mainbutton_list = item.find_elements(By.CSS_SELECTOR, "[role='button']")
        for button in mainbutton_list:
            children = button.find_elements(By.XPATH, "*")
            if len(children) > 0:
                continue
            if "See more" not in button.text:
                continue

            try:
                button.click()
            except selenium.common.exceptions.ElementClickInterceptedException:
                ## obscured by other element - try to hide by CSS
                return False

            return True
        return False

    def _take_screenshot(self, screenshot_id):
        screenshot_path = f"/tmp/screenshot_{screenshot_id}.png"
        self.driver.save_screenshot(screenshot_path)
        _LOGGER.debug("screenshot stored in %s", screenshot_path)

    def _accept_cookies(self):
        _LOGGER.debug("closing cookies popup")
        cookie_button_list = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label='Allow all cookies']")
        for item in cookie_button_list:
            if not item.text:
                continue
            item.click()

    def _close_login_popup(self):
        _LOGGER.debug("closing login popup")
        for _rep in range(3):
            close_button_list = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label='Close']")
            for item in close_button_list:
                button_item = item.find_elements(By.TAG_NAME, "i")
                if not button_item:
                    _LOGGER.warning("could not close login popup")
                    time.sleep(0.5)
                    break
                button_item[0].click()
                return

    def _hide_login_bar(self):
        _LOGGER.debug("hidding login bar")
        ## bottom bar
        bottom_list = self.driver.find_elements(By.CSS_SELECTOR, "div[data-nosnippet]")
        for item in bottom_list:
            self.driver.execute_script("arguments[0].style.visibility='hidden'", item)

    def _init_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless")

        driver = None

        gecko_config_path = "/tmp/gecko_path.txt"

        try:
            gecko_path = read_data(gecko_config_path)
        except FileNotFoundError:
            gecko_path = None

        if gecko_path:
            # driver = webdriver.Firefox()
            driver = webdriver.Firefox(executable_path=gecko_path, options=options)
        else:
            # driver = webdriver.Firefox()
            gecko_path = GeckoDriverManager().install()
            driver = webdriver.Firefox(executable_path=gecko_path, options=options)
            write_data(gecko_config_path, gecko_path)

        return driver


## datetime format fields:
##        https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
##
def pub_string_to_date(pub_text) -> datetime.datetime:
    with setlocale("C"):
        ## try to parse date in format "<days number>d", eg. "5d"
        if len(pub_text) <= 3 and pub_text.endswith("d"):
            sufix = pub_text.index("d")
            num_day = int(pub_text[:sufix])
            today_date = datetime.datetime.now(tz=datetime.timezone.utc).astimezone()
            midnight = datetime.datetime.combine(today_date, datetime.time())
            midnight = midnight - datetime.timedelta(days=num_day)
            return add_timezone(midnight)

        ## try to parse date in format
        ## "<month name> <day number> at <hour_number>:<min_number> {AM|PM}", eg. "September 8 at 3:50 PM"
        try:
            item_date = None
            item_date = datetime.datetime.strptime(pub_text, "%B %d at %I:%M %p")
            ## set current year
            now_date = datetime.datetime.now(tz=datetime.timezone.utc).astimezone()
            now_timezone = now_date.tzinfo
            item_date = item_date.replace(year=now_date.year, tzinfo=now_timezone)
            if item_date > now_date:
                ## subtract one year
                item_date = item_date.replace(year=item_date.year - 1)

        except ValueError:
            ## could not parse
            pass

        else:
            return item_date

        ## try to parse date in format "<month name> <day number>", eg. "July 9"
        try:
            item_date = None
            item_date = datetime.datetime.strptime(pub_text, "%B %d")
            ## set current year
            now_date = datetime.datetime.now(tz=datetime.timezone.utc).astimezone()
            now_timezone = now_date.tzinfo
            item_date = item_date.replace(year=now_date.year, tzinfo=now_timezone)
            if item_date > now_date:
                ## subtract one year
                item_date = item_date.replace(year=item_date.year - 1)

        except ValueError:
            ## could not parse
            pass

        else:
            return item_date

        _LOGGER.error("unable to convert post pub date: '%s'", pub_text)
        return None


def extract_event_id_from_url(event_url: str):
    ## https://www.facebook.com/events/{event_id}/?params
    url_content = event_url.split("/")
    if len(url_content) < 6:
        _LOGGER.error("could not get event id - unknown url format: %s", url_content)
        return None
    if url_content[3] != "events":
        _LOGGER.error("could not get event id - unknown url format: %s", url_content)
        return None

    url_tail = url_content[4]
    url_tail_items = url_tail.split("?")
    return url_tail_items[0]


def extract_post_id_from_url(post_url: str):
    ## https://www.facebook.com/{page_id}/posts/{post_id}?params
    url_content = post_url.split("/")
    if len(url_content) < 6:
        _LOGGER.error("could not get post id - unknown url format: %s", url_content)
        return None
    if url_content[4] != "posts":
        _LOGGER.error("could not get post id - unknown url format: %s", url_content)
        return None

    url_tail = url_content[5]
    url_tail_items = url_tail.split("?")
    return url_tail_items[0]


def get_content_title(content, length):
    if len(content) < length:
        return content
    space_pos = content.rfind(" ", 0, 40)
    if space_pos < 0:
        space_pos = 40
    return content[:space_pos] + "..."


LOCALE_LOCK = threading.Lock()


@contextmanager
def setlocale(name):
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)
