#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from enum import Enum, unique, auto
import toml

from rssforward.utils import get_app_datadir


_LOGGER = logging.getLogger(__name__)


# ==================================================


@unique
class ConfigKey(Enum):
    GENERAL = "general"
    SITE = "site"
    AUTH = "auth"


@unique
class ConfigField(Enum):
    STARTSERVER = "startserver"
    PORT = "port"
    REFRESHTIME = "refreshtime"
    DATAROOT = "dataroot"
    ENABLED = "enabled"

    AUTH_TYPE = "type"
    AUTH_LOGIN = "login"  # nosec
    AUTH_PASS = "pass"  # nosec
    AUTH_ITEMURL = "itemurl"  # nosec


# ==================================================


@unique
class AuthType(Enum):
    RAW = auto()  # additional fields: "login", "pass"
    KEEPASSXC = auto()  # additional field: "itemurl"


# ==================================================


def load_config(config_path):
    config_dict = load_raw(config_path)
    if not config_dict:
        return config_dict

    # set default value of data directory if not set
    general_section = config_dict.get(ConfigKey.GENERAL.value, {})
    data_root = general_section.get(ConfigField.DATAROOT.value)
    if data_root is None:
        data_dir = get_app_datadir()
        data_root = os.path.join(data_dir, "data")
    data_root = os.path.abspath(data_root)
    general_section[ConfigField.DATAROOT.value] = data_root

    return config_dict


def load_raw(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    except FileNotFoundError:
        _LOGGER.warning("could not load config file '%s' - using default configuration", config_path)
    return {}
