#!/usr/bin/python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
import datetime
import pytz

from appdirs import user_data_dir

import rssforward.persist


_LOGGER = logging.getLogger(__name__)


def get_app_datadir():
    data_dir = user_data_dir("rss-forward")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_recentdate_path():
    data_dir = get_app_datadir()
    recentdate_path = os.path.join(data_dir, "recentdate.obj")
    return recentdate_path


def read_recent_date():
    recentdate_path = get_recentdate_path()
    return rssforward.persist.load_object_simple(recentdate_path)


def get_recent_date():
    today_date = datetime.date.today()
    midnight = datetime.datetime.combine(today_date, datetime.time())
    # move back 1 day to prevent short time window where data could be skipped
    midnight = midnight - datetime.timedelta(days=1)
    today_datetime = add_timezone(midnight)
    return today_datetime


def save_recent_date(recent_datetime):
    _LOGGER.info("storing recent date: %s", recent_datetime)
    recentdate_path = get_recentdate_path()
    rssforward.persist.store_object_simple(recent_datetime, recentdate_path)


def add_timezone(dt: datetime.datetime) -> datetime.datetime:
    tz_info = pytz.timezone("Europe/Warsaw")
    return tz_info.localize(dt)
