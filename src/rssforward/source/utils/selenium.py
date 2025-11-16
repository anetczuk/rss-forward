#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from rssforward.utils import read_data, write_data


lib_logger = logging.getLogger("selenium.webdriver")
lib_logger.setLevel(logging.WARNING)

lib_logger = logging.getLogger("urllib3.connectionpool")
lib_logger.setLevel(logging.WARNING)


_LOGGER = logging.getLogger(__name__)


def init_selenium_driver(*, headless=True) -> webdriver.Firefox:
    options = Options()
    if headless:
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


def selenium_get_content(url: str):
    with init_selenium_driver() as driver:
        driver.get(url)
        return driver.page_source
